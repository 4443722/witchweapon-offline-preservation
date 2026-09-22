package com.codex.witchweapon;

import android.util.AtomicFile;
import android.util.Base64;
import org.json.JSONObject;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

/** Versioned local progress. All mutations are committed before returning success. */
final class LocalSave {
    static final long STAGE=3110001002L;
    static final long MAZE_TRIAL=3110001003L;
    private final AtomicFile file;
    private JSONObject state;
    LocalSave(File dir){file=new AtomicFile(new File(dir,"offline_save_v1.json"));}
    private void load() throws Exception {
        if(state!=null)return;
        if(file.getBaseFile().exists() || new File(file.getBaseFile()+".bak").exists()) {
            state=new JSONObject(new String(file.readFully(),StandardCharsets.UTF_8));
            if(state.getInt("version")!=1)throw new IOException("Unsupported local save version");
        } else {
            JSONObject s=new JSONObject();s.put("version",1);s.put("name","本地玩家");
            s.put("gold",1000000L);s.put("exp",0L);s.put("wins",0);s.put("attempts",0);
            s.put("stage",STAGE);s.put("stars",0);s.put("createdAt",System.currentTimeMillis());
            commit(s);
        }
    }
    private void commit(JSONObject next) throws Exception {
        FileOutputStream out=null;
        try {
            out=file.startWrite();out.write((next.toString(2)+"\n").getBytes(StandardCharsets.UTF_8));
            file.finishWrite(out);state=next;
        } catch(Exception e){if(out!=null)file.failWrite(out);throw e;}
    }
    private long wornFashion(){
        // Unity PlayerPrefs for the currently worn hall fashion. Visual wear is
        // already client-side; combat reads the same key so FashionSerial and
        // CSV init attributes match the model on screen.
        File data=file.getBaseFile().getParentFile();
        if(data!=null)data=data.getParentFile();
        if(data==null)return 70000001L;
        File prefs=new File(data,"shared_prefs/com.codex.witchweapon.local.v2.playerprefs.xml");
        if(!prefs.exists())return 70000001L;
        try{
            ByteArrayOutputStream out=new ByteArrayOutputStream();
            try(FileInputStream in=new FileInputStream(prefs)){
                byte[] buf=new byte[4096];int n;
                while((n=in.read(buf))>0)out.write(buf,0,n);
            }
            String xml=out.toString("UTF-8");
            java.util.regex.Matcher m=java.util.regex.Pattern.compile("name=\"com\\.shuiqinling\\.fashion_1\"[^>]*>([^<]+)").matcher(xml);
            if(m.find())return Long.parseLong(m.group(1).trim());
            m=java.util.regex.Pattern.compile("name=\"com\\.shuiqinling\\.fashion_1\"\\s+value=\"(\\d+)\"").matcher(xml);
            if(m.find())return Long.parseLong(m.group(1));
        }catch(Exception e){}
        return 70000001L;
    }
    private static long num(Map<String,String> args,String key,long fallback){
        try{return Long.parseLong(args.get(key));}catch(Exception e){return fallback;}
    }
    private ProtoWire sync(long now){
        long midnight=Math.floorDiv(now+28800,86400)*86400-28800;
        ProtoWire roleTime=new ProtoWire().set(6,midnight+18000).set(10,midnight).set(12,8);
        return new ProtoWire().set(1,now).set(4,state.optLong("stamina",200)).set(5,now).set(6,roleTime.bytes()).set(7,state.optLong("activityStamina",200)).set(8,now);
    }
    synchronized String fixtureKey(String path,Map<String,String> args) throws Exception {
        load();
        long stage=num(args,"instanceid",0);
        if(path.startsWith("/combat/") && stage==MAZE_TRIAL)
            return path+"#"+stage+"@"+Math.max(1,Math.min(12,state.optInt("mazeRound",1)));
        return path+"#"+stage;
    }
    synchronized byte[] respond(String path,Map<String,String> args,byte[] seed,JSONObject catalog) throws Exception {
        load();long now=System.currentTimeMillis()/1000;
        if(path.startsWith("/game/"))path=path.substring(5);
        if(path.equals("/combat/role/info")){
            JSONObject next=new JSONObject(state.toString());
            next.put("curFashion",wornFashion());
            return LocalEconomy.combat(next,args,seed,catalog);
        }
        if(catalog!=null && LocalEconomy.handles(path)){
            JSONObject next=new JSONObject(state.toString());
            byte[] response=LocalEconomy.respond(next,catalog,path,args,seed);
            if(!next.toString().equals(state.toString()))commit(next);
            return response;
        }
        if(path.equals("/role/create")){
            String name=args.get("name");
            if(name!=null&&!name.trim().isEmpty()){
                JSONObject next=new JSONObject(state.toString());next.put("name",name.trim());commit(next);
            }
        }
        if(path.equals("/role/create")||path.equals("/role/userlogin")){
            // The descriptor uses RoleID=1, Time=2 (verified by the generator).
            return ProtoWire.parse(seed).set(2,sync(now).bytes()).bytes();
        }
        if(path.equals("/role/login")||path.equals("/time/sync"))return sync(now).bytes();
        if(path.equals("/timer/sync"))return ProtoWire.parse(seed).set(1,now).bytes();
        if(path.equals("/role/role")){
            ProtoWire m=ProtoWire.parse(seed),r=ProtoWire.parse(m.data(1));
            long level=5,exp=state.getLong("exp");
            JSONObject costs=catalog==null?null:catalog.optJSONObject("roleLevels");
            while(costs!=null&&level<100){long cost=costs.optLong(String.valueOf(level),Long.MAX_VALUE);
                if(cost<=0||exp<cost)break;exp-=cost;level++;}
            r.text(111,state.getString("name")).set(105,state.getLong("gold")).set(106,exp).set(104,level);
            r.set(103,state.optLong("rmb",100000)).set(124,state.optLong("vipExp",0));
            r.set(107,state.optLong("stamina",200)).set(108,now).set(121,state.optLong("activityStamina",200)).set(122,now);
            JSONObject unlocked=state.optJSONObject("roleUnlocks");
            if(unlocked!=null)for(Iterator<String> it=unlocked.keys();it.hasNext();){
                String key=it.next();int field=Integer.parseInt(key);JSONObject entries=unlocked.getJSONObject(key);
                List<Long> flags=r.integers(field);
                for(Iterator<String> ei=entries.keys();ei.hasNext();){int index=Integer.parseInt(ei.next())-1;
                    while(flags.size()<=index)flags.add(0L);flags.set(index,1L);}
                r.clear(field);for(long flag:flags)r.add(field,flag);
            }
            r.set(127,state.optLong("curBoard",1));
            JSONObject runes=state.optJSONObject("fashionRunes");
            if(runes!=null)for(ProtoWire.Field f:m.fields)if(f.number==3&&f.type==2){
                ProtoWire fashion=ProtoWire.parse(f.data);
                org.json.JSONArray slots=runes.optJSONArray(String.valueOf(fashion.number(1,0)));
                if(slots!=null){ProtoWire layout=new ProtoWire();for(int i=0;i<slots.length();i++)layout.add(1,slots.getLong(i));fashion.set(3,layout.bytes());f.data=fashion.bytes();}
            }
            return m.set(1,r.bytes()).set(2,sync(now).data(6)).set(4,level).bytes();
        }
        if(path.equals("/level/getAllProgress")){
            ProtoWire m=ProtoWire.parse(seed);
            for(ProtoWire.Field f:m.fields)if(f.number==1&&f.type==2){
                ProtoWire chap=ProtoWire.parse(f.data);
                for(ProtoWire.Field l:chap.fields)if(l.number==2&&l.type==2){
                    ProtoWire level=ProtoWire.parse(l.data);
                    if(level.number(1,0)==STAGE){
                        boolean passed=state.getInt("wins")>0;
                        level.set(2,passed?1:0).set(4,1).set(7,passed?1:0).set(6,state.getInt("attempts"));
                        level.set(3,state.getInt("stars")==3?1:0);
                        l.data=level.bytes();
                    }
                    if(level.number(1,0)==MAZE_TRIAL){
                        boolean passed=state.optInt("mazeWins")>0;
                        level.set(2,passed?1:0).set(4,1).set(7,passed?1:0).set(6,state.optInt("mazeAttempts"));
                        level.set(3,state.optInt("mazeStars")==3?1:0);
                        l.data=level.bytes();
                    }
                }
                f.data=chap.bytes();
            }
            return m.bytes();
        }
        if(path.equals("/level/startBattle")||path.equals("/level/rebattle")){
            long stage=num(args,"instanceid",STAGE);
            if(stage!=STAGE && stage!=MAZE_TRIAL)throw new IOException("Local encounter unavailable");
            String key=args.get("idempotency");
            if(key==null)throw new IOException("Missing start request identity");
            if(!key.equals(state.optString("startKey")) || stage!=state.optLong("activeStage",STAGE)){
                JSONObject next=new JSONObject(state.toString());next.put("startKey",key);
                String counter=stage==MAZE_TRIAL?"mazeAttempts":"attempts";
                next.put("active",true);next.put("activeStage",stage);
                if(stage==MAZE_TRIAL){
                    if(next.optInt("mazeRound",1)>12){
                        next.put("mazeRound",1);next.put("mazeRuns",next.optInt("mazeRuns")+1);
                        next.put("mazeHP",1);
                        ArrayList<String> energyKeys=new ArrayList<String>();
                        for(Iterator<String> it=next.keys();it.hasNext();){String k=it.next();if(k.startsWith("mazeEnergy_"))energyKeys.add(k);}
                        for(String k:energyKeys)next.remove(k);
                    }
                    next.put("battleMazeRound",next.optInt("mazeRound",1));
                }
                next.put(counter,next.optInt(counter)+1);next.put("battleStartedAt",now);
                next.remove("battleResponse");commit(next);
            }
            return seed;
        }
        if(path.equals("/level/pushMainLineProgress")){
            long stage=num(args,"instanceid",0);
            if((stage!=STAGE && stage!=MAZE_TRIAL) || stage!=state.optLong("activeStage",STAGE))throw new IOException("Unexpected settlement stage");
            if(state.has("battleResponse"))return Base64.decode(state.getString("battleResponse"),Base64.DEFAULT);
            if(!state.optBoolean("active"))throw new IOException("No active local battle");
            boolean win=num(args,"pass",0)==1;int stars=(int)Math.max(0,Math.min(3,num(args,"stars",0)));
            JSONObject next=new JSONObject(state.toString());next.put("active",false);
            ProtoWire result=new ProtoWire().set(1,200).set(2,now).set(4,new byte[0]);
            if(win){
                String wins=stage==MAZE_TRIAL?"mazeWins":"wins",best=stage==MAZE_TRIAL?"mazeStars":"stars";
                next.put(wins,next.optInt(wins)+1);next.put(best,Math.max(next.optInt(best),stars));
                next.put("gold",next.getLong("gold")+1000);next.put("exp",next.getLong("exp")+5);
                result.set(5,5).add(3,new ProtoWire().set(1,13).set(3,1000).set(4,1000).bytes());
                if(stage==MAZE_TRIAL){
                    int round=next.optInt("battleMazeRound",1);
                    next.put("mazeRound",round+1);
                    double hp=1;
                    try{hp=Double.parseDouble(args.get("hp"));}catch(Exception ignored){}
                    next.put("mazeHP",Math.max(0.01,Math.min(1,hp)));
                    File energy=new File(file.getBaseFile().getParentFile(),"offline_battle_energy.json");
                    if(energy.exists()){
                        try{
                            byte[] bytes=new byte[(int)energy.length()];
                            try(DataInputStream in=new DataInputStream(new FileInputStream(energy))){in.readFully(bytes);}
                            JSONObject snap=new JSONObject(new String(bytes,StandardCharsets.UTF_8));
                            if(snap.optString("startKey").equals(next.optString("startKey"))){
                                for(Iterator<String> it=snap.keys();it.hasNext();){String k=it.next();
                                    if(k.startsWith("mazeEnergy_"))next.put(k,Math.max(0,Math.min(1000,snap.optDouble(k,1000))));
                                }
                            }
                        }catch(Exception ignored){}
                    }
                    if(round%3==0){
                        long supply=10000L;
                        next.put("gold",next.getLong("gold")+supply);
                        result.add(3,new ProtoWire().set(1,13).set(3,supply).set(4,supply).bytes());
                        next.put("mazeSupplyBoxes",next.optInt("mazeSupplyBoxes")+1);
                        // Local camp: apply once with the checkpoint, not on retries/login.
                        next.put("mazeHP",Math.min(1,next.optDouble("mazeHP",1)+0.30));
                        for(Iterator<String> it=next.keys();it.hasNext();){String k=it.next();
                            if(k.startsWith("mazeEnergy_"))next.put(k,Math.min(1000,next.optDouble(k,1000)+300));
                        }
                    }
                }
            }
            next.put("lastSettlementAt",now);next.put("lastBattle",new JSONObject(args));
            byte[] response=result.bytes();next.put("battleResponse",Base64.encodeToString(response,Base64.NO_WRAP));
            commit(next);return response;
        }
        return seed;
    }
}
