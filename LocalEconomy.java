package com.codex.witchweapon;

import android.util.Base64;
import org.json.JSONObject;
import java.util.*;

/** Persistent local inventory and character growth. Called under LocalSave lock. */
final class LocalEconomy {
    static String encode(ProtoWire p){return Base64.encodeToString(p.bytes(),Base64.NO_WRAP);}
    static ProtoWire decode(String s)throws Exception{return ProtoWire.parse(Base64.decode(s,Base64.DEFAULT));}
    static long number(String s,long fallback){try{return Long.parseLong(s);}catch(Exception e){return fallback;}}
    static List<Long> ids(String raw){
        List<Long> out=new ArrayList<Long>();if(raw==null)return out;
        for(String token:raw.split("[|,;]")){long id=number(token,-1);if(id>=0)out.add(id);}
        return out;
    }
    static boolean handles(String p){return p.equals("/task/all") || p.equals("/task/update") || p.equals("/shop/buy") || p.equals("/resource/sell/gold") || p.equals("/role/board/change") || p.equals("/role/rename") || p.startsWith("/fashion/") || p.startsWith("/draw/") || p.equals("/guide/draw") || p.startsWith("/servant/") || p.equals("/backpack/servantequip") || p.equals("/backpack/item") || p.equals("/backpack/item/use");}
    static void init(JSONObject s,JSONObject cat)throws Exception{
        if(!s.has("ownedServants")){
            JSONObject owned=new JSONObject(),templates=cat.getJSONObject("servants");
            for(String id:new String[]{"10010001","10010101","10010201","10010301"})owned.put(id,templates.getString(id));
            s.put("ownedServants",owned);
        }
        if(!s.has("items")){
            JSONObject bag=new JSONObject(),items=cat.getJSONObject("items");
            for(Iterator<String> it=items.keys();it.hasNext();){String id=it.next();bag.put(id,9999);}
            s.put("items",bag);
        }
        if(!s.has("equips") && cat.has("equips")){
            JSONObject bag=new JSONObject(),defs=cat.getJSONObject("equips");
            for(Iterator<String> it=defs.keys();it.hasNext();)bag.put(it.next(),9999);
            s.put("equips",bag);
        }
        // Versioned upgrade of the earlier 50-point one-time bond award.
        // Only the unpaid difference is added; existing saves keep their progress.
        JSONObject claims=s.optJSONObject("favorClaims"),paid=s.optJSONObject("favorClaimAmounts");
        if(paid==null)paid=new JSONObject();
        if(claims!=null){
            JSONObject defs=cat.getJSONObject("favorQuests"),owned=s.getJSONObject("ownedServants");
            for(Iterator<String> it=claims.keys();it.hasNext();){String q=it.next();
                JSONObject def=defs.optJSONObject(q);if(def==null||!claims.optBoolean(q))continue;
                String sid=String.valueOf(def.getLong("servant"));if(!owned.has(sid))continue;
                long before=paid.optLong(q,50),after=def.getLong("amount");
                if(after>before){ProtoWire sv=decode(owned.getString(sid));
                    addFavor(sv,after-before,cat.getJSONObject("favorCaps").getLong(sid));owned.put(sid,encode(sv));}
                paid.put(q,Math.max(before,after));
            }
        }
        s.put("favorClaimAmounts",paid);
    }
    static byte[] respond(JSONObject s,JSONObject cat,String path,Map<String,String> a,byte[] seed)throws Exception{
        if(path.equals("/servant/starpoint"))
            throw new java.io.IOException("Legacy star points are absent from this client; use its star promotion screen");
        init(s,cat);
        clampBag(s,cat);
        if(path.equals("/task/all")){
            ProtoWire result=ProtoWire.parse(seed);
            JSONObject quests=cat.getJSONObject("favorQuests"),claimed=s.optJSONObject("favorClaims");
            for(ProtoWire.Field f:result.fields)if(f.number==1&&f.type==2){
                ProtoWire job=ProtoWire.parse(f.data);String id=String.valueOf(job.number(1,0));
                if(quests.has(id)){job.set(2,claimed!=null&&claimed.optBoolean(id)?1:0).set(3,1).text(4,"82");f.data=job.bytes();}
            }
            return result.bytes();
        }
        if(path.equals("/task/update")){
            String id=a.get("jobid");JSONObject def=cat.getJSONObject("favorQuests").optJSONObject(id==null?"":id);
            if(def==null)return seed;
            JSONObject claimed=s.optJSONObject("favorClaims");if(claimed==null)claimed=new JSONObject();
            if(claimed.optBoolean(id))return new ProtoWire().bytes();
            String sid=String.valueOf(def.getLong("servant"));JSONObject owned=s.getJSONObject("ownedServants");
            if(!owned.has(sid))throw new java.io.IOException("Own this servant before claiming the bond reward");
            ProtoWire sv=decode(owned.getString(sid));long amount=def.getLong("amount");
            addFavor(sv,amount,cat.getJSONObject("favorCaps").getLong(sid));
            owned.put(sid,encode(sv));claimed.put(id,true);s.put("favorClaims",claimed);
            s.getJSONObject("favorClaimAmounts").put(id,amount);
            return new ProtoWire().add(1,new ProtoWire().set(1,24).set(2,Long.parseLong(sid)).set(3,amount).set(4,1).bytes()).bytes();
        }
        if(path.equals("/role/board/change")){
            long id=number(a.get("board"),-1);boolean valid=false;
            org.json.JSONArray boards=cat.getJSONArray("boards");
            for(int i=0;i<boards.length();i++)if(boards.getLong(i)==id)valid=true;
            if(!valid)throw new java.io.IOException("Unknown display character "+id);
            s.put("curBoard",id);return new ProtoWire().text(1,"ok").bytes();
        }
        if(path.equals("/role/rename")){
            String name=a.get("rolename");
            if(name==null||name.isEmpty())name=a.get("name");
            if(name==null||name.isEmpty())name=a.get("roleName");
            if(name!=null)name=name.trim();
            if(name!=null&&name.length()>=2)s.put("name",name);
            JSONObject bag=s.optJSONObject("items");
            if(bag!=null){
                String card="40340010";
                long left=bag.optLong(card);
                if(left>0)bag.put(card,left-1);
            }
            return new ProtoWire().text(1,"ok").bytes();
        }
        if(path.startsWith("/fashion/")){
            String id=a.containsKey("fashioncardid")?a.get("fashioncardid"):a.get("fashionid");
            if(id==null||!cat.getJSONObject("fashions").has(id))throw new java.io.IOException("Unknown fashion "+id);
            if(path.equals("/fashion/runes/update")){
                List<Long> runes=ids(a.get("runes"));
                if(runes.size()!=9)throw new java.io.IOException("Expected nine fashion rune slots");
                JSONObject all=s.optJSONObject("fashionRunes");if(all==null)all=new JSONObject();
                all.put(id,new org.json.JSONArray(runes));s.put("fashionRunes",all);
            }else if(!path.equals("/fashion/compose"))throw new java.io.IOException("Unsupported fashion route");
            return new ProtoWire().text(1,"ok").bytes();
        }
        if(path.startsWith("/draw/")||path.equals("/guide/draw"))return draw(s,cat,path,a);
        JSONObject owned=s.getJSONObject("ownedServants"),bag=s.getJSONObject("items");
        if(path.equals("/servant/servants")){
            // DrawtList/AddLoot call GetObservableServantsByID. That map is
            // filled only from this list (ServantCore starts empty), so every
            // catalog witch must be present as a stub or a ten-pull of a new
            // character throws and the result panel never closes.
            ProtoWire result=new ProtoWire();
            Set<String> seen=new HashSet<String>();
            List<String> keys=new ArrayList<String>();for(Iterator<String> it=owned.keys();it.hasNext();)keys.add(it.next());
            Collections.sort(keys);
            for(String id:keys){result.add(1,decode(owned.getString(id)).bytes());seen.add(id);}
            JSONObject templates=cat.getJSONObject("servants");
            List<String> rest=new ArrayList<String>();
            for(Iterator<String> it=templates.keys();it.hasNext();){String id=it.next();if(!seen.contains(id))rest.add(id);}
            Collections.sort(rest);
            for(String id:rest){
                ProtoWire stub=decode(templates.getString(id));
                stub.clear(13);
                result.add(1,stub.bytes());
            }
            return result.bytes();
        }
        if(path.equals("/backpack/item")||path.equals("/backpack/servantequip")){
            ProtoWire result=new ProtoWire();
            JSONObject inventory=path.equals("/backpack/item")?bag:s.getJSONObject("equips");
            for(Iterator<String> it=inventory.keys();it.hasNext();){String id=it.next();long count=inventory.optLong(id);
                if(path.equals("/backpack/item"))count=Math.min(count,stackCap(cat,id));
                // Equipment's native full-list parser updates entries in place;
                // include zero so selling the last copy clears a cached stack.
                if(count>0||path.equals("/backpack/servantequip")){result.add(1,Long.parseLong(id));result.add(2,count);}}
            return result.bytes();
        }
        String request=path+":"+a.get("idempotency");
        JSONObject done=s.optJSONObject("economyRequests");if(done==null){done=new JSONObject();s.put("economyRequests",done);}
        if(a.containsKey("idempotency")&&done.has(request))return Base64.decode(done.getString(request),Base64.DEFAULT);
        if(path.equals("/servant/star")){
            List<Long> ids=strictIds(a.get("servantcardids"));
            if(ids.isEmpty()||new HashSet<Long>(ids).size()!=ids.size())throw new java.io.IOException("Select each servant once");
            for(long id:ids){
                String sid=String.valueOf(id);
                if(!owned.has(sid))throw new java.io.IOException("Own this servant before star promotion");
                ProtoWire sv=decode(owned.getString(sid));long star=sv.number(5,1);
                if(star<0||star>=5)throw new java.io.IOException("Maximum star level reached");
                JSONObject cost=cat.getJSONObject("stars").getJSONObject(sid).getJSONObject(String.valueOf(star));
                String item=String.valueOf(cost.getLong("item"));long quantity=cost.getLong("count"),gold=cost.getLong("gold");
                if(quantity<=0||gold<0||bag.optLong(item)<quantity||s.getLong("gold")<gold)
                    throw new java.io.IOException("Insufficient resources for star promotion");
                bag.put(item,bag.getLong(item)-quantity);s.put("gold",s.getLong("gold")-gold);
                sv.set(5,star+1);owned.put(sid,encode(sv));
            }
            s.put("inventoryRevision",Math.addExact(s.optLong("inventoryRevision"),1));
            byte[] response=new ProtoWire().text(1,"ok").bytes();
            if(a.containsKey("idempotency")){if(done.length()>=100)done=new JSONObject();done.put(request,Base64.encodeToString(response,Base64.NO_WRAP));s.put("economyRequests",done);}
            return response;
        }
        if(path.equals("/resource/sell/gold")){
            long gold=0;boolean any=false;
            for(String kind:new String[]{"items","equips"}){
                String counts=kind.equals("items")?"itemnums":"equipnums";
                String key=kind.equals("items")?"itemids":"equipids";
                List<Long> sell=strictIds(a.containsKey(key)?a.get(key):a.get(kind)),nums=strictIds(a.get(counts));
                if(sell.size()!=nums.size())throw new java.io.IOException("Invalid sale quantities");
                JSONObject inventory=s.getJSONObject(kind),defs=cat.getJSONObject(kind);
                for(int i=0;i<sell.size();i++){
                    String id=String.valueOf(sell.get(i));long count=nums.get(i);
                    JSONObject def=defs.optJSONObject(id);
                    if(def==null||def.optLong("sell_price")<=0)throw new java.io.IOException("This resource cannot be sold");
                    if(count<1||count>inventory.optLong(id))throw new java.io.IOException("Insufficient resources for sale");
                    inventory.put(id,inventory.getLong(id)-count);
                    gold=Math.addExact(gold,Math.multiplyExact(def.getLong("sell_price"),count));any=true;
                }
            }
            if(!any)throw new java.io.IOException("Select a resource to sell");
            addResource(s,"gold",1000000,gold);
            s.put("inventoryRevision",Math.addExact(s.optLong("inventoryRevision"),1));
            byte[] response=new ProtoWire().text(1,"ok").bytes();
            if(a.containsKey("idempotency")){if(done.length()>=100)done=new JSONObject();done.put(request,encode(ProtoWire.parse(response)));s.put("economyRequests",done);}
            return response;
        }
        if(path.equals("/shop/buy")||path.equals("/backpack/item/use")){
            byte[] response;
            if(path.equals("/shop/buy")){
                if(number(a.containsKey("setid")?a.get("setid"):a.get("shopsetid"),0)!=44000001L || number(a.get("shopid"),0)!=4501010003L || number(a.get("goodsid"),0)!=45030124L)
                    throw new java.io.IOException("Unknown local supply product");
                long count=Math.max(1,Math.min(9999,number(a.get("count"),1)));
                grantSupply(s,cat,count);
                response=new ProtoWire().text(1,"ok").add(5,new ProtoWire().set(1,13).set(3,1000000L*count).set(4,1000000L*count).bytes()).bytes();
            }else{
                List<Long> use=strictIds(a.containsKey("itemids")?a.get("itemids"):a.get("items")),counts=strictIds(a.get("itemnums"));
                if(use.isEmpty()||use.size()!=counts.size())throw new java.io.IOException("Invalid item quantities");
                for(int i=0;i<use.size();i++){
                    String id=String.valueOf(use.get(i));long count=counts.get(i);
                    if(count<1||count>9999||count>bag.optLong(id))throw new java.io.IOException("Insufficient items");
                    if(use.get(i)==40350004L)grantSupply(s,cat,count);
                    else useInventoryItem(s,cat,id,count,number(a.get("targetItem"),number(a.get("targetitem"),0)));
                    bag.put(id,bag.optLong(id)-count);
                }
                response=new ProtoWire().text(1,"ok").bytes();
            }
            s.put("inventoryRevision",Math.addExact(s.optLong("inventoryRevision"),1));
            if(a.containsKey("idempotency")){if(done.length()>=100)done=new JSONObject();done.put(request,Base64.encodeToString(response,Base64.NO_WRAP));s.put("economyRequests",done);}
            return response;
        }
        List<Long> servants=ids(a.get("servantcardids"));
        JSONObject templates=cat.getJSONObject("servants"),itemDefs=cat.getJSONObject("items");
        long itemExp=0,weaponExp=0,favorExp=0;
        List<Long> itemIds=ids(a.get("items")),amounts=ids(a.containsKey("nums")?a.get("nums"):a.get("itemnums"));
        for(int i=0;i<itemIds.size();i++){
            String id=String.valueOf(itemIds.get(i));long count=i<amounts.size()?amounts.get(i):1;
            JSONObject item=itemDefs.optJSONObject(id);if(item==null)continue;
            count=Math.max(0,Math.min(count,bag.optLong(id)));
            bag.put(id,bag.optLong(id)-count);
            itemExp+=item.optLong("servant_exp")*count;
            weaponExp+=item.optLong("weapon_value")*count;
            favorExp+=item.optLong("favorability_value")*count;
        }
        if(path.equals("/servant/weapon")){
            JSONObject equips=s.getJSONObject("equips"),defs=cat.getJSONObject("equips");
            List<Long> equipIds=ids(a.get("equips")),equipCounts=ids(a.get("equipnums"));
            for(int i=0;i<equipIds.size();i++){
                String id=String.valueOf(equipIds.get(i));JSONObject def=defs.optJSONObject(id);
                if(def==null)throw new java.io.IOException("Unknown weapon enhancement material");
                long count=i<equipCounts.size()?equipCounts.get(i):1;
                if(count<0||count>equips.optLong(id))throw new java.io.IOException("Insufficient enhancement equipment");
                equips.put(id,equips.optLong(id)-count);
                weaponExp+=def.optLong("weapon_value")*count;
            }
        }
        for(long sid:servants){
            String id=String.valueOf(sid);
            if(!owned.has(id)&&path.equals("/servant/compose")&&templates.has(id))owned.put(id,templates.getString(id));
            if(!owned.has(id))continue;
            ProtoWire sv=decode(owned.getString(id));
            if(path.equals("/servant/exp"))levelUp(sv,2,3,itemExp,cat.getJSONObject("levels"));
            else if(path.equals("/servant/weapon"))levelUp(sv,12,16,weaponExp,cat.getJSONObject("weaponLevels").getJSONObject(id));
            else if(path.equals("/servant/rank")){
                long next=sv.number(4,1)+1;
                JSONObject def=cat.getJSONObject("ranks").getJSONObject(id).optJSONObject(String.valueOf(next));
                if(def==null||sv.number(2,1)<def.getLong("minLevel")||sv.number(7,0)!=63)
                    throw new java.io.IOException("Rank requires the next level and six equipped items");
                sv.set(4,next);sv.set(7,0);
            }
            else if(path.equals("/servant/equip")){
                long slots=sv.number(7,0);
                org.json.JSONArray defs=cat.getJSONObject("ranks").getJSONObject(id).getJSONObject(String.valueOf(sv.number(4,1))).getJSONArray("equips");
                JSONObject equips=s.getJSONObject("equips");
                for(long slot:ids(a.containsKey("equipserials")?a.get("equipserials"):a.get("equipslots"))){
                    if(slot<1||slot>6)throw new java.io.IOException("Invalid equipment slot");
                    long bit=1L<<(slot-1);if((slots&bit)!=0)continue;
                    String equip=String.valueOf(defs.getLong((int)slot-1));
                    if(equips.optLong(equip)<1)throw new java.io.IOException("Equipment missing");
                    equips.put(equip,equips.getLong(equip)-1);slots|=bit;
                }
                sv.set(7,slots);
            }else if(path.equals("/servant/spell")){
                int which=(int)number(a.get("spelltype"),-1);long[] levels=packedInts(sv,8,5,1);
                if(which<0||which>=5)throw new java.io.IOException("Invalid spell slot");
                levels[which]=Math.min(100,levels[which]+1);
                sv.clear(8);for(long lv:levels)sv.add(8,lv);
            }else if(path.equals("/servant/image/change"))sv.set(18,Math.max(1,number(a.get("serial"),1)));
            else if(path.equals("/servant/favor/exp")){
                addFavor(sv,favorExp,cat.getJSONObject("favorCaps").getLong(id));
            }
            owned.put(id,encode(sv));
        }
        if(path.startsWith("/servant/weapon/")){
            List<Long> ws=ids(a.containsKey("weapons")?a.get("weapons"):a.get("weapon"));
            JSONObject weaponDefs=cat.getJSONObject("weapons");
            for(long wid:ws){
                JSONObject def=weaponDefs.optJSONObject(String.valueOf(wid));if(def==null)continue;
                String sid=String.valueOf(def.getLong("servant"));
                if(!owned.has(sid)&&templates.has(sid))owned.put(sid,templates.getString(sid));
                if(!owned.has(sid))continue;ProtoWire sv=decode(owned.getString(sid));
                for(ProtoWire.Field f:sv.fields)if(f.number==13&&f.type==2){
                    ProtoWire w=ProtoWire.parse(f.data);if(w.number(1,0)!=wid)continue;
                    if(path.endsWith("/spell/promote")){
                        if(w.number(4,1)<2){
                            long gold=def.getLong("awakenGold");
                            if(s.getLong("gold")<gold)throw new java.io.IOException("Insufficient gold for awakening");
                            org.json.JSONArray costs=def.getJSONArray("awakenItems");
                            for(int i=0;i<costs.length();i++){
                                org.json.JSONArray cost=costs.getJSONArray(i);String item=String.valueOf(cost.getLong(0));long amount=cost.getLong(1);
                                if(amount<=0)continue;
                                if(bag.optLong(item)<amount)throw new java.io.IOException("Insufficient awakening materials");
                                bag.put(item,bag.getLong(item)-amount);
                            }
                            s.put("gold",s.getLong("gold")-gold);w.set(4,2);
                        }
                    }
                    else if(path.endsWith("/promote"))w.set(3,Math.min(2,w.number(3,0)+1));
                    else if(path.endsWith("/skin/change"))w.set(6,Math.max(1,number(a.get("skinIndex"),1)));
                    f.data=w.bytes();
                }
                owned.put(sid,encode(sv));
            }
        }
        byte[] response=new ProtoWire().text(1,"ok").bytes();
        if(a.containsKey("idempotency")){
            if(done.length()>100)done=new JSONObject();
            done.put(request,Base64.encodeToString(response,Base64.NO_WRAP));s.put("economyRequests",done);
        }
        return response;
    }
    static void grantSupply(JSONObject s,JSONObject cat,long count)throws Exception{
        JSONObject bag=s.getJSONObject("items"),equips=s.getJSONObject("equips");
        for(Iterator<String> it=cat.getJSONObject("items").keys();it.hasNext();){
            String id=it.next();if(id.equals("40350004"))continue;
            bag.put(id,Math.min(stackCap(cat,id),Math.max(9999,bag.optLong(id))));
        }
        for(Iterator<String> it=cat.getJSONObject("equips").keys();it.hasNext();){String id=it.next();equips.put(id,Math.max(9999,equips.optLong(id)));}
        s.put("gold",s.optLong("gold")+1000000L*count);
        s.put("supplyUses",s.optLong("supplyUses")+count);
    }
    static void addFavor(ProtoWire sv,long add,long cap){
        long level=Math.min(cap,sv.number(9,1)),exp=sv.number(10,0)+Math.max(0,add);
        while(level<cap&&exp>=50){exp-=50;level++;}
        sv.set(9,level).set(10,exp);
    }
    static void levelUp(ProtoWire sv,int levelField,int expField,long add,JSONObject costs)throws Exception{
        long lv=sv.number(levelField,1),exp=sv.number(expField,0)+Math.max(0,add);
        long cap=levelField==12?Math.min(65,sv.number(2,5)):65;
        while(lv<cap){long cost=costs.optLong(String.valueOf(lv),Long.MAX_VALUE);if(cost<=0||exp<cost)break;exp-=cost;lv++;}
        sv.set(levelField,lv).set(expField,exp);
    }
    /** Free collection pool: prefer an unowned weapon; duplicates become materials. */
    static byte[] draw(JSONObject s,JSONObject cat,String path,Map<String,String> a)throws Exception{
        if(path.equals("/draw/rate/get"))return new ProtoWire().bytes();
        if(!Arrays.asList("/draw/gold/single","/draw/gold/ten","/draw/rmb/single","/draw/rmb/ten",
                "/draw/activity","/draw/activity/special","/guide/draw").contains(path))
            throw new java.io.IOException("Unsupported local draw route: "+path);
        // UITool.GetLootDataList pairs each weapon with one Type=1 servant
        // result. A weapon-only response fills ExtraWeapon but leaves DrawLoot
        // empty, so all ten display entries are discarded before ShowResult.
        String request="v9-paired:"+path+":"+a.get("idempotency");
        JSONObject done=s.optJSONObject("drawRequests");if(done==null)done=new JSONObject();
        if(a.containsKey("idempotency")&&done.has(request))return Base64.decode(done.getString(request),Base64.DEFAULT);
        JSONObject owned=s.getJSONObject("ownedServants"),defs=cat.getJSONObject("weapons"),templates=cat.getJSONObject("servants");
        Set<Long> have=new HashSet<Long>();
        for(Iterator<String> it=owned.keys();it.hasNext();){
            ProtoWire sv=decode(owned.getString(it.next()));
            for(ProtoWire.Field f:sv.fields)if(f.number==13&&f.type==2)have.add(ProtoWire.parse(f.data).number(1,0));
        }
        List<Long> pool=new ArrayList<Long>(),missing=new ArrayList<Long>();
        for(Iterator<String> it=defs.keys();it.hasNext();){String key=it.next();
            if(!templates.has(String.valueOf(defs.getJSONObject(key).getLong("servant"))))continue;
            long id=Long.parseLong(key);pool.add(id);if(!have.contains(id))missing.add(id);
        }
        if(pool.isEmpty())throw new java.io.IOException("Empty local draw pool");
        Collections.sort(pool);Collections.sort(missing);
        Random random=new java.security.SecureRandom();ProtoWire result=new ProtoWire();
        int count=path.endsWith("/ten")?10:1;
        if(a.containsKey("times"))count=(int)number(a.get("times"),count);
        if(count<1)count=1;if(count>10)count=10;
        for(int i=0;i<count;i++){
            long wid=missing.isEmpty()?pool.get(random.nextInt(pool.size())):missing.remove(random.nextInt(missing.size()));
            // Preserve one servant/weapon pair per pull, including duplicates.
            if(!have.contains(wid)){
                String sid=String.valueOf(defs.getJSONObject(String.valueOf(wid)).getLong("servant"));
                boolean isNew=!owned.has(sid);
                ProtoWire sv=decode(isNew?templates.getString(sid):owned.getString(sid));
                if(isNew)sv.clear(13);
                ProtoWire template=decode(templates.getString(sid));
                boolean found=false;
                for(ProtoWire.Field f:template.fields)if(f.number==13&&f.type==2&&ProtoWire.parse(f.data).number(1,0)==wid){sv.add(13,f.data);found=true;break;}
                if(!found)throw new java.io.IOException("Missing weapon template "+wid);
                owned.put(sid,encode(sv));have.add(wid);
            }
            long sid=defs.getJSONObject(String.valueOf(wid)).getLong("servant");
            result.add(1,new ProtoWire().set(1,1).set(2,sid).set(4,1).bytes());
            result.add(1,new ProtoWire().set(1,4).set(2,wid).set(4,1).bytes());
        }
        s.put("drawCount",s.optLong("drawCount")+count);
        byte[] response=result.bytes();
        if(a.containsKey("idempotency")){
            if(done.length()>=100)done=new JSONObject();done.put(request,Base64.encodeToString(response,Base64.NO_WRAP));s.put("drawRequests",done);
        }
        return response;
    }
    static long stackCap(JSONObject cat,String id)throws Exception{
        JSONObject item=cat.getJSONObject("items").optJSONObject(id);
        long cap=item==null?9999:item.optLong("max_stack",9999);
        return cap>0?cap:9999;
    }
    static void addItem(JSONObject bag,JSONObject cat,String id,long add)throws Exception{
        long cap=stackCap(cat,id);
        bag.put(id,Math.min(cap,Math.max(0,bag.optLong(id)+add)));
    }
    static void clampBag(JSONObject s,JSONObject cat)throws Exception{
        JSONObject bag=s.optJSONObject("items");if(bag==null||!cat.has("items"))return;
        for(Iterator<String> it=bag.keys();it.hasNext();){String id=it.next();
            long cap=stackCap(cat,id),n=bag.optLong(id);
            if("40330006".equals(id))cap=Math.max(0,cap-500);
            if(n>cap)bag.put(id,cap);
        }
    }
    static void addResource(JSONObject s,String key,long initial,long amount)throws Exception{
        if(amount<0)throw new java.io.IOException("Invalid resource amount");
        s.put(key,Math.addExact(s.optLong(key,initial),amount));
    }
    static void collectionChanged(JSONObject s)throws Exception{
        s.put("collectionRevision",Math.addExact(s.optLong("collectionRevision"),1));
    }
    static List<Long> strictIds(String raw)throws java.io.IOException{
        List<Long> out=new ArrayList<Long>();if(raw==null||raw.isEmpty())return out;
        for(String token:raw.split("[|,;]",-1)){
            long value=number(token,-1);if(value<0)throw new java.io.IOException("Invalid resource quantity");out.add(value);
        }
        return out;
    }
    static void useInventoryItem(JSONObject s,JSONObject cat,String id,long count,long target)throws Exception{
        JSONObject item=cat.getJSONObject("items").getJSONObject(id);
        if(item.optLong("stamina")>0){addResource(s,"stamina",200,item.getLong("stamina")*count);return;}
        if(item.optLong("act_stamina")>0){addResource(s,"activityStamina",200,item.getLong("act_stamina")*count);return;}
        if(item.optInt("item_type")==3&&item.optInt("item_sub_type")==4){
            addResource(s,"gold",1000000,item.getLong("sell_price")*count);return;
        }
        org.json.JSONArray rewards=item.getJSONArray("rewards");
        boolean choice=item.optInt("item_sub_type")==15,granted=false;
        for(int j=0;j<rewards.length();j++){
            JSONObject r=rewards.getJSONObject(j);long rid=r.getLong("id");
            if(choice&&rid!=target)continue;
            grantItemReward(s,cat,r,count);granted=true;
            if(choice)break;
        }
        if(!granted)throw new java.io.IOException(choice?"Choose an item from this chest":"Use this material in its growth or equipment screen");
    }
    static void grantItemReward(JSONObject s,JSONObject cat,JSONObject r,long count)throws Exception{
        int type=r.getInt("type");long rid=r.getLong("id"),value=r.getLong("value");
        long amount=(r.getLong("count")>0?r.getLong("count"):value)*count;
        if(type==2||type==3){
            String name=type==2?"equips":"items",key=String.valueOf(rid);
            if(!cat.getJSONObject(name).has(key))throw new java.io.IOException("Unknown reward item "+rid);
            JSONObject bag=s.getJSONObject(name);bag.put(key,Math.addExact(bag.optLong(key),amount));return;
        }
        String resource=null;long initial=0;
        if(type==12){resource="stamina";initial=200;}
        if(type==13){resource="gold";initial=1000000;}
        if(type==20)resource="vipExp";
        if(type==98||type==99){resource="rmb";initial=100000;}
        if(resource!=null){addResource(s,resource,initial,amount);return;}
        if(type==5){if(!cat.getJSONObject("fashions").has(String.valueOf(rid)))throw new java.io.IOException("Unknown fashion");return;}
        if(type==80||type==81||type==83||type==84||type==87){
            String field=type==80?"1":type==81?"2":type==87?"3":type==83?"4":"5";
            JSONObject flags=s.optJSONObject("roleUnlocks");if(flags==null)flags=new JSONObject();
            JSONObject entries=flags.optJSONObject(field);if(entries==null)entries=new JSONObject();
            if(value<1||value>10000)throw new java.io.IOException("Invalid cosmetic index");
            entries.put(String.valueOf(value),true);flags.put(field,entries);s.put("roleUnlocks",flags);collectionChanged(s);return;
        }
        JSONObject owned=s.getJSONObject("ownedServants"),templates=cat.getJSONObject("servants");
        if(type==85){
            String sid=String.valueOf(rid);if(!owned.has(sid))throw new java.io.IOException("Own this servant before using its costume gift");
            if(value<1||value>63)throw new java.io.IOException("Invalid servant image");
            ProtoWire sv=decode(owned.getString(sid));sv.set(11,sv.number(11,1)|(1L<<(value-1)));owned.put(sid,encode(sv));collectionChanged(s);return;
        }
        if(type==4){
            JSONObject weapon=cat.getJSONObject("weapons").getJSONObject(String.valueOf(rid));
            String sid=String.valueOf(weapon.getLong("servant"));
            ProtoWire template=decode(templates.getString(sid));
            ProtoWire sv=owned.has(sid)?decode(owned.getString(sid)):decode(templates.getString(sid));
            if(!owned.has(sid))sv.clear(13);
            boolean has=false;
            for(ProtoWire.Field f:sv.fields)if(f.number==13&&f.type==2&&ProtoWire.parse(f.data).number(1,0)==rid)has=true;
            if(!has)for(ProtoWire.Field f:template.fields)if(f.number==13&&f.type==2&&ProtoWire.parse(f.data).number(1,0)==rid){sv.add(13,f.data);break;}
            owned.put(sid,encode(sv));collectionChanged(s);return;
        }
        throw new java.io.IOException("Unknown chest reward type "+type);
    }
    static byte[] combat(JSONObject s,Map<String,String> a,byte[] seed,JSONObject cat)throws Exception{
        JSONObject owned=s.optJSONObject("ownedServants");if(owned==null)return seed;
        double scale=0;int count=0;ProtoWire combat=ProtoWire.parse(seed);
        List<Long> party=ids(a.get("servantcardids")),weapons=ids(a.get("weaponids"));
        List<byte[]> selected=new ArrayList<byte[]>();
        for(int index=0;index<party.size();index++){
            long sid=party.get(index),wid=index<weapons.size()?weapons.get(index):0;
            byte[] match=null;
            for(ProtoWire.Field f:combat.fields)if(f.number==2&&f.type==2){
                ProtoWire info=ProtoWire.parse(f.data);
                if(info.number(1,0)==sid&&(wid==0||info.number(14,0)==wid)){match=f.data;break;}
            }
            if(match==null)throw new java.io.IOException("Combat template not restored for servant "+sid+" weapon "+wid);
            selected.add(match);
        }
        if(!party.isEmpty()){combat.clear(2);for(byte[] info:selected)combat.add(2,info);}
        for(long sid:ids(a.get("servantcardids"))){
            String key=String.valueOf(sid);if(!owned.has(key))continue;
            ProtoWire sv=decode(owned.getString(key));count++;
            scale+=1+0.05*Math.max(0,sv.number(2,5)-5)+0.08*Math.max(0,sv.number(4,1)-1)
                +0.1*Math.max(0,sv.number(5,1)-1)
                +0.01*Long.bitCount(sv.number(7,0)&63);
            for(ProtoWire.Field f:combat.fields)if(f.number==2&&f.type==2){
                ProtoWire info=ProtoWire.parse(f.data);if(info.number(1,0)!=sid)continue;
                long wid=info.number(14,0);
                for(ProtoWire.Field w:sv.fields)if(w.number==13&&w.type==2){
                    ProtoWire weapon=ProtoWire.parse(w.data);if(weapon.number(1,0)!=wid)continue;
                    int spellRank=(int)Math.max(1,Math.min(2,weapon.number(4,1)));
                    info.set(15,spellRank).set(16,weapon.number(6,1));
                    JSONObject def=cat.getJSONObject("weapons").getJSONObject(String.valueOf(wid));
                    double mod=cat.getJSONObject("weaponMods").getJSONObject(key)
                        .getLong(String.valueOf(sv.number(12,5)))/10000.0;
                    info.set(3,Math.round(def.getJSONArray("physical").getLong(spellRank-1)*mod));
                    info.set(4,Math.round(def.getJSONArray("magical").getLong(spellRank-1)*mod));
                }
                f.data=info.bytes();
            }
        }
        if(count>0){
            scale/=count;double[] attrs=combat.doubles(1);
            for(int i=0;i<Math.min(5,attrs.length);i++)attrs[i]*=scale;
            // Local balance uses the mean contribution of the selected party,
            // matching the existing growth aggregation. Values are original CSV.
            for(long sid:party){String id=String.valueOf(sid);if(!owned.has(id))continue;
                ProtoWire sv=decode(owned.getString(id));
                org.json.JSONArray bonuses=cat.getJSONObject("favorAttrs").getJSONArray(id);
                for(int i=0;i<bonuses.length();i++){JSONObject b=bonuses.getJSONObject(i);
                    int attr=b.getInt("type")-1;
                    if(b.getInt("level")<=sv.number(9,1)&&attr>=0&&attr<Math.min(5,attrs.length))
                        attrs[attr]+=(double)b.getLong("value")/count;
                }
            }
            combat.doubles(1,attrs);
            applyFashion(s,cat,combat,attrs,a);
        }else{
            applyFashion(s,cat,combat,combat.doubles(1),a);
        }
        // The current 2.0 tooltip evaluates summon formulas with servant Level
        // (SqlStringUtil.SPLevel types 1/2), not the legacy manual SpellLv slot.
        // Keep the outer summon and all linked effects at that same level.
        ProtoWire unit=ProtoWire.parse(combat.data(102));
        Map<Long,Long> spellLevels=new HashMap<Long,Long>(),buffLevels=new HashMap<Long,Long>(),agentLevels=new HashMap<Long,Long>();
        for(long sid:party){
            if(!owned.has(String.valueOf(sid)))continue;
            ProtoWire sv=decode(owned.getString(String.valueOf(sid)));
            long level=sv.number(2,5),serial=(sid/100)%1000;
            boolean detailed=serial<=103||serial==112;
            spellLevels.put((detailed?90110000L:90510000L)+serial,level);
            agentLevels.put((detailed?90210000L:90610000L)+serial,level);
            if(serial==100){buffLevels.put(90100001L,level);buffLevels.put(90100002L,level);}
            else if(serial==102){buffLevels.put(90102001L,level);spellLevels.put(90102002L,level);}
            else if(serial==103)buffLevels.put(90103001L,level);
            else if(serial==112)buffLevels.put(90112001L,level);
            else{buffLevels.put(90700000L+serial,level);buffLevels.put(90800000L+serial,level);}
            for(ProtoWire.Field f:combat.fields)if(f.number==2&&f.type==2){
                ProtoWire info=ProtoWire.parse(f.data);if(info.number(1,0)!=sid)continue;
                spellLevels.put(info.number(10,0),level);
                for(long attack:packedInts(info,8,3,0))if(attack>0)spellLevels.put(attack,sv.number(12,5));
                spellLevels.put(info.number(7,0),sv.number(12,5));
            }
        }
        for(ProtoWire.Field f:unit.fields)if(f.type==2&&(f.number==1||f.number==2||f.number==3)){
            ProtoWire info=ProtoWire.parse(f.data);
            Map<Long,Long> levels=f.number==1?spellLevels:(f.number==2?buffLevels:agentLevels);
            Long level=levels.get(info.number(f.number==2?3:2,0));
            if(level!=null){info.set(1,level);f.data=info.bytes();}
        }
        // Original summon IDs, with explicit local stats. Their own entity/AI
        // inherits the player's camp; persistent servant level scales the seed.
        long[][] pets={{332010380501L,10011601L},{332010381501L,10012201L},
                      {332010381701L,10012501L},{332010340501L,10013101L}};
        for(ProtoWire.Field f:unit.fields)if(f.number==5&&f.type==2){
            ProtoWire mob=ProtoWire.parse(f.data);
            for(long[] pet:pets)if(mob.number(6,0)==pet[0]&&owned.has(String.valueOf(pet[1]))){
                long level=decode(owned.getString(String.valueOf(pet[1]))).number(2,5);
                double growth=1+0.04*Math.max(0,level-5);
                mob.set(3,level);
                for(int field:new int[]{30,31,32})mob.set(field,Math.round(mob.number(field,0)*growth));
                f.data=mob.bytes();
            }
        }
        combat.set(102,unit.bytes());
        return combat.bytes();
    }
    // Fashion.csv spell rows that set is_attribute_type. Values are the CSV
    // init amounts, not a reconstructed server grow-by-level formula.
    static void applyFashion(JSONObject s,JSONObject cat,ProtoWire combat,double[] attrs,Map<String,String> a)throws Exception{
        long fid=number(a==null?null:a.get("fashioncardid"),s.optLong("curFashion",70000001L));
        JSONObject serials=cat.optJSONObject("fashions");
        if(serials!=null&&serials.has(String.valueOf(fid)))
            combat.set(103,serials.getLong(String.valueOf(fid)));
        JSONObject all=cat.optJSONObject("fashionAttrs");
        if(all==null||!all.has(String.valueOf(fid)))return;
        org.json.JSONArray bonuses=all.getJSONArray(String.valueOf(fid));
        for(int i=0;i<bonuses.length();i++){
            JSONObject b=bonuses.getJSONObject(i);
            int attr=b.getInt("type")-1;
            if(attr>=0&&attr<attrs.length&&attr<5)
                attrs[attr]+=b.getLong("value");
        }
        combat.doubles(1,attrs);
    }
    static long[] packedInts(ProtoWire msg,int n,int count,long fallback)throws Exception{
        long[] out=new long[count];Arrays.fill(out,fallback);int i=0;
        for(ProtoWire.Field f:msg.fields)if(f.number==n){
            if(f.type==0){if(i<count)out[i++]=f.value;}
            else if(f.type==2){long v=0;int shift=0;for(byte b:f.data){v|=(long)(b&127)<<shift;if((b&128)==0){if(i<count)out[i++]=v;v=0;shift=0;}else shift+=7;}}
        }
        return out;
    }
}
