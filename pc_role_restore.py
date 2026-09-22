"""Reconstruct native NGUI character bundles from verified PC sprite data."""
from pathlib import Path
import os,sys,json,re,io,math,hashlib,zipfile,collections
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools/python'))
import UnityPy
from PIL import Image
from pc_scene_inspect import character_nodes

def pc_image(path):
    path=path.removeprefix('res://');source=ROOT/'pc_story_source'
    meta=(source/(path+'.import')).read_text('utf8');rel=re.search(r'path="res://([^"]+)"',meta).group(1)
    b=(source/rel).read_bytes();assert b[:4]==b'GST2' and b[56:60]==b'RIFF'
    return Image.open(io.BytesIO(b[56:])).convert('RGBA')

def build_role(sn,char,faces,info,template):
    nodes=character_nodes(char);base=nodes['Base'];face=nodes['Face'];body=pc_image(base['texture'])
    facepath=face.get('texture');faceposition=face.get('position',[0,0]);hasfaces=bool(facepath)
    default=info.get('current_expression','')
    frames={}
    if hasfaces:
        parent=facepath.rsplit('/',1)[0]
        expected_size=pc_image(facepath).size
        for number,expression in list(faces.items()):
            frame=pc_image(parent+'/'+expression+'.png')
            if number.startswith('pc_') and frame.size!=expected_size:
                del faces[number];continue
            frames[number]=frame
        if '01' not in frames:frames['01']=pc_image(facepath)
    else:
        frames['01']=Image.new('RGBA',(2,2),(0,0,0,0))
    sizes={im.size for im in frames.values()};assert len(sizes)==1,(sn,sizes)
    fw,fh=next(iter(sizes));cols=math.ceil(math.sqrt(len(frames)));rows=math.ceil(len(frames)/cols)
    aw=2**math.ceil(math.log2(max(2,cols*(fw+2))));ah=2**math.ceil(math.log2(max(2,rows*(fh+2))))
    atlas=Image.new('RGBA',(aw,ah));sprites=[]
    for i,(number,im) in enumerate(sorted(frames.items())):
        x=(i%cols)*(fw+2);y=(i//cols)*(fh+2);atlas.paste(im,(x,y));sprites.append(dict(name=sn+number if len(number)==2 else number,x=x,y=y,width=fw,height=fh,**{k:0 for k in ['borderLeft','borderRight','borderTop','borderBottom','paddingLeft','paddingRight','paddingTop','paddingBottom']}))
    env=UnityPy.load(template);objects=list(env.objects);names={o.path_id:o.read_typetree()['m_Name'] for o in objects if o.type.name=='GameObject'}
    bodyid=next(o.path_id for o in objects if o.type.name=='Texture2D' and o.read_typetree()['m_Name']=='role01')
    for obj in objects:
        t=obj.read_typetree()
        if obj.type.name=='Texture2D':
            tex=obj.read();isbody=obj.path_id==bodyid;tex.m_Name=('role' if isbody else 'face')+sn;tex.set_image(body if isbody else atlas,target_format=4,mipmap_count=1);tex.save();continue
        if obj.type.name=='GameObject':t['m_Name']=t['m_Name'].replace('01',sn)
        elif obj.type.name=='Transform':
            name=names[t['m_GameObject']['m_PathID']]
            if name=='Body':t['m_LocalPosition']=dict(x=-faceposition[0],y=faceposition[1],z=0.0)
            elif name=='Role01':
                scale=base.get('scale',[1,1]);bp=base['position']
                t['m_LocalPosition']=dict(x=(bp[0]+faceposition[0]*scale[0]-640)/.96,y=(360-bp[1]-faceposition[1]*scale[1])/.96,z=0.0)
        elif obj.type.name=='MonoBehaviour':
            name=names.get(t['m_GameObject']['m_PathID'],'')
            if 'mSprites' in t:t['mSprites']=sprites
            elif name=='Body' and 'mWidth' in t:
                t['mWidth'],t['mHeight']=body.size;t['aspectRatio']=body.width/body.height
            elif 'mSpriteName' in t:
                t['mSpriteName']=sn+'01';t['mWidth']=fw;t['mHeight']=fh;t['aspectRatio']=fw/fh
        elif obj.type.name=='AssetBundle':
            for k in ['m_Name','m_AssetBundleName']:t[k]=t[k].replace('role01','role'+sn)
            t['m_Container']=[(k.replace('role01','role'+sn),v) for k,v in t['m_Container']]
        obj.save_typetree(t)
    key=next(iter(env.file.files));env.file.files['CAB-'+hashlib.md5(('restored-role-'+sn).encode()).hexdigest()]=env.file.files.pop(key)
    blob=env.file.save(packer='original')
    for obj in UnityPy.load(blob).objects:
        if obj.type.name=='Texture2D':
            tex=obj.read();expected=body if tex.m_Name=='role'+sn else atlas
            assert tex.image.convert('RGBA').tobytes()==expected.tobytes()
    bundle='assets/assetbundle/assets/resources/ui/prefab/guide/role'+sn+'.ab';target=ROOT/'overrides'/bundle;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(blob)
    return dict(bundle=bundle,character=char,role=sn,faces=faces,has_faces=hasfaces,default_expression=default,source_base=base['texture'],source_face=facepath,sha256=hashlib.sha256(blob).hexdigest(),pixel_roundtrip_exact=True,reconstructed_ngui=True)

def main():
    evidence=json.loads((ROOT/'evidence/pc_role_mapping_evidence.json').read_text('utf8'));roles=[];skipped=[]
    alignment=json.loads((ROOT/'evidence/pc_exact_alignment.json').read_text('utf8'))['observations']
    exact_roles=collections.defaultdict(collections.Counter);exact_faces=collections.defaultdict(collections.Counter)
    for observation in alignment:
        sn=observation['role'];char=observation['character'];face=observation['face']
        exact_roles[sn][char]+=1
        if str(face).isdigit():exact_faces[(sn,face)][char+':'+observation['expression']]+=1
    for sn,votes in exact_roles.items():
        if sn not in evidence['role_votes']:evidence['role_votes'][sn]=dict(votes)
    evidence['role_votes']['62']={'witch_second':1} # chapter2_ep20 lines 57-59: original attacker dialogue.
    family=['04','06','07','08','10','14','15']
    common={}
    for key,counts in evidence['face_votes'].items():
        if key.split('_')[0] not in family:continue
        votes={}
        for name,n in counts.items():
            expression=name.split(':',1)[1];votes[expression]=votes.get(expression,0)+n
        winner=max(votes,key=votes.get)
        if votes[winner]>=2 and votes[winner]/sum(votes.values())>=.8:
            common.setdefault(key.split('_')[1],set()).add(winner)
    for (sn,code),votes in exact_faces.items():
        if sn not in family:continue
        selected={k:v for k,v in votes.items() if k.startswith('ren_')}
        if selected:
            winner=max(selected,key=selected.get)
            if selected[winner]/sum(selected.values())>=.8:common.setdefault(code,set()).add(winner.split(':',1)[1])
    shared={k:next(iter(v)) for k,v in common.items() if len(v)==1}
    with zipfile.ZipFile(Path(os.environ.get('WW_SOURCE_APK',ROOT/'inputs'/'20240516161158_mnbq.apk'))) as z:
        template=z.read('assets/assetbundle/assets/resources/ui/prefab/guide/role01.ab');existing=set(z.namelist())
        for sn,votes in evidence['role_votes'].items():
            if 'assets/assetbundle/assets/resources/ui/prefab/guide/role'+sn+'.ab' in existing:continue
            char=max(votes,key=votes.get)
            static_exact=sn=='62' or not character_nodes(char)['Face'].get('texture') and any(o['role']==sn and o['character']==char and o['score']==1 for o in evidence['observations'])
            if (votes[char]<2 and not static_exact) or votes[char]/sum(votes.values())<.9:skipped.append((sn,'uncertain character'));continue
            faces={}
            for key,counts in evidence['face_votes'].items():
                if not key.startswith(sn+'_'):continue
                counts={k:v for k,v in counts.items() if k.startswith(char+':')}
                if not counts:continue
                winner=max(counts,key=counts.get)
                if counts[winner]>=2 and counts[winner]/sum(counts.values())>=.8:faces[key.split('_')[1]]=winner.split(':',1)[1]
            for (role,code),votes2 in exact_faces.items():
                if role!=sn:continue
                counts={k:v for k,v in votes2.items() if k.startswith(char+':')}
                if not counts:continue
                winner=max(counts,key=counts.get)
                if counts[winner]/sum(counts.values())>=.8:faces[code]=winner.split(':',1)[1]
            inherited={}
            if sn in family:
                for code,expression in shared.items():
                    if code not in faces and expression in evidence['characters'][char].get('expression_list',[]):
                        faces[code]=expression;inherited[code]=expression
            if sn=='88':
                assert character_nodes(char)['Face']['texture']==character_nodes('soya_uniform')['Face']['texture']
                for key,counts in evidence['face_votes'].items():
                    if not key.startswith('86_'):continue
                    winner=max(counts,key=counts.get)
                    if counts[winner]>=2 and counts[winner]/sum(counts.values())>=.8:
                        code='86'+key.split('_')[1];expression=winner.split(':',1)[1]
                        faces[code]=expression;inherited[code]=expression
            # Named frames preserve the PC source's per-line expressions without ambiguous numeric inference.
            for expression in evidence['characters'][char].get('expression_list',[]):faces['pc_'+expression]=expression
            try:
                result=build_role(sn,char,faces,evidence['characters'][char],template)
                result['shared_costume_expression_mapping']=inherited
                roles.append(result)
            except Exception as e:skipped.append((sn,str(e)))
    (ROOT/'evidence/pc_restored_roles.json').write_text(json.dumps(dict(assets=roles,skipped=skipped),ensure_ascii=False,indent=2),'utf8')
    print('Built roles',len(roles),'skipped',skipped)

if __name__=='__main__':main()
