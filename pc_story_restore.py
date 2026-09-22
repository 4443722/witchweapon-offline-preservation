"""Repack recovered background pixels for the original Unity story player.

No Godot scripts are executed and no original Unity lesson is replaced.
"""
from pathlib import Path
import os, sys, json, re, io, hashlib, zipfile, csv
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools/python'))
import UnityPy
from PIL import Image
SOURCE=ROOT/'pc_story_source'
PREFIX='assets/assetbundle/assets/resources/ui/uiimage/guide/'
MAPPING={
    'bg_sid_spsoundchannel':'SID/spSoundChannel',
    'bg_shot_losgrail':'Shot/losgrail',
    'bg_shot_soul_sacrifice':'Shot/Soul_Sacrifice',
    'bg_fabiola_yumeren2':'Fabiola/YumeRen2',
    'bg_shot_liliu_leg2':'Shot/liliu_leg2',
    'bg_shot_girlchar_battlewearingcry':'Shot/girlchar_battleWearingCry',
    'bg_shot_unknowm':'Baizhu/unknowm',
    'bg_baizhu_previously1':'Baizhu/BG_Baizhu_Previously1',
    'bg_baizhu_previously2':'Baizhu/BG_Baizhu_Previously2',
    'bg_baizhu_previously3':'Baizhu/BG_Baizhu_Previously3',
    'bg_shot_baizhu_sleeping':'Baizhu/baizhu_sleeping',
    'bg_shot_submarinedetector':'Baizhu/submarineDetector',
    'bg_shot_submarinedetector_lighting':'Baizhu/submarineDetector_Lighting',
    'bg_shot_sea_eyeball':'Baizhu/sea_eyeball',
}
if (ROOT/'pc_background_mapping.json').exists():
    MAPPING.update(json.loads((ROOT/'pc_background_mapping.json').read_text('utf8')))

def texture(source):
    metadata=(SOURCE/('assets/images/bg/'+source+'.png.import')).read_text('utf8')
    path=re.search(r'path="res://([^"]+)"',metadata).group(1)
    data=(SOURCE/path).read_bytes()
    assert data[:4]==b'GST2' and data[56:60]==b'RIFF' and data[64:68]==b'WEBP',path
    image=Image.open(io.BytesIO(data[56:])).convert('RGBA')
    return image,path

def main():
    report=[]
    previous=ROOT/'evidence/pc_story_restored_assets.json'
    cache={a['bundle']:a for a in json.loads(previous.read_text('utf8'))['assets']} if previous.exists() else {}

    with zipfile.ZipFile(Path(os.environ.get('WW_SOURCE_APK',ROOT/'inputs'/'20240516161158_mnbq.apk'))) as z:
        template=z.read(PREFIX+'bg_apt_baizhu_bedroom.ab')
        for dest,source in MAPPING.items():
            name=PREFIX+dest+'.ab';oldasset=cache.get(name);target=ROOT/'overrides'/name
            metadata=(SOURCE/('assets/images/bg/'+source+'.png.import')).read_text('utf8')
            sourcepath=re.search(r'path="res://([^"]+)"',metadata).group(1)
            if oldasset and oldasset.get('source')==sourcepath and target.exists() and hashlib.sha256(target.read_bytes()).hexdigest()==oldasset['sha256']:
                report.append(oldasset);continue
            image,path=texture(source);env=UnityPy.load(template)
            for obj in env.objects:
                if obj.type.name=='Texture2D':
                    tex=obj.read();tex.m_Name=dest
                    tex.set_image(image,target_format=4,mipmap_count=1);tex.save()
                elif obj.type.name=='AssetBundle':
                    tree=obj.read_typetree();tree['m_Name']='assets/resources/ui/uiimage/guide/'+dest+'.ab'
                    tree['m_AssetBundleName']=tree['m_Name'][:-3]
                    tree['m_Container']=[('assets/resources-/ui/uiimage/guide/'+dest+'.jpg',tree['m_Container'][0][1])]
                    obj.save_typetree(tree)
            old=next(iter(env.file.files));env.file.files['CAB-'+hashlib.md5(dest.encode()).hexdigest()]=env.file.files.pop(old)
            data=env.file.save(packer='original');target=ROOT/'overrides'/(PREFIX+dest+'.ab');target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
            check=UnityPy.load(data);restored=next(o.read().image.convert('RGBA') for o in check.objects if o.type.name=='Texture2D')
            assert restored.size==image.size and restored.tobytes()==image.tobytes(),dest
            report.append(dict(bundle=PREFIX+dest+'.ab',source=path,width=image.width,height=image.height,sha256=hashlib.sha256(data).hexdigest(),pixel_roundtrip_exact=True))
            if len(report)<=14:image.save(ROOT/'evidence'/('recovered_'+dest+'.png'))
        role_manifest=ROOT/'evidence/pc_restored_roles.json'
        if role_manifest.exists():
            for asset in json.loads(role_manifest.read_text('utf8'))['assets']:
                assert hashlib.sha256((ROOT/'overrides'/asset['bundle']).read_bytes()).hexdigest()==asset['sha256']
                report.append(asset)
        conversion=ROOT/'evidence/pc_converted_lessons.json'
        if conversion.exists():report.extend(json.loads(conversion.read_text('utf8')).get('extra_roles',[]))
        repairs=ROOT/'evidence/pc_graph_repairs.json'
        excluded=json.loads(repairs.read_text('utf8')).get('excluded_dependencies',{}) if repairs.exists() else {}
        # These dependencies are now physically included in the APK.
        name='assets/assetbundle/config/clientexel/assetscutinfo.ab';env=UnityPy.load(z.read(name));removed=0
        restored_paths={'/'+x['bundle'].removeprefix('assets/assetbundle/') for x in report}
        for obj in env.objects:
            if obj.type.name!='MonoBehaviour':continue
            tree=obj.read_typetree()
            if 'bytes' not in tree:continue
            raw=bytes(tree['bytes']);raw=bytes(b^255 for b in raw) if tree.get('isEncrypt') else raw
            rows=list(csv.reader(io.StringIO(raw.decode('utf-8-sig'))));pathcol=rows[0].index('path');keycol=rows[0].index('key')
            keep=rows[:3]+[row for row in rows[3:] if not row or (row[pathcol] not in restored_paths and row[pathcol] not in excluded.get(row[keycol],[]))]
            removed=len(rows)-len(keep);buf=io.StringIO();csv.writer(buf,lineterminator='\n').writerows(keep)
            data=('\ufeff'+buf.getvalue()).encode('utf8');tree['bytes']=list(bytes(b^255 for b in data) if tree.get('isEncrypt') else data);obj.save_typetree(tree)
        assert removed>0
        target=ROOT/'overrides'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(env.file.save(packer='original'))
    (ROOT/'evidence/pc_story_restored_assets.json').write_text(json.dumps(dict(assets=report,cut_rows_removed=removed),ensure_ascii=False,indent=2),'utf8')
    print('Restored',len(report),'story assets; cut rows removed',removed)

if __name__=='__main__':main()
