package com.codex.witchweapon;

import android.app.Application;
import android.util.Log;
import org.json.JSONObject;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

/** In-process loopback service. It never opens any outbound connection. */
public final class OfflineApplication extends Application {
    private static final String TAG="WitchOffline";
    private LocalSave localSave;
    @Override public void onCreate() {
        super.onCreate();
        localSave=new LocalSave(getFilesDir());
        Thread server=new Thread(new Runnable(){public void run(){serve();}}, "witch-local-http");
        server.setDaemon(true);server.start();
    }
    private void serve() {
        try {
            ServerSocket listener=new ServerSocket(19876,16,InetAddress.getByName("127.0.0.1"));
            record("listen", "127.0.0.1:19876");
            while(true) {
                final Socket client=listener.accept();
                Thread worker=new Thread(new Runnable(){public void run(){handle(client);}}, "witch-local-request");
                worker.setDaemon(true);worker.start();
            }
        } catch(Exception e){record("server_error",Log.getStackTraceString(e));}
    }
    private static byte[] readAll(InputStream in) throws IOException {
        ByteArrayOutputStream out=new ByteArrayOutputStream();byte[] buf=new byte[8192];int n;
        while((n=in.read(buf))!=-1)out.write(buf,0,n);
        return out.toByteArray();
    }
    private JSONObject responses() throws Exception {
        File local=new File(getFilesDir(),"offline_responses.json");
        try(InputStream in=local.exists()?new FileInputStream(local):getAssets().open("offline_responses.json")) {
            return new JSONObject(new String(readAll(in),StandardCharsets.UTF_8));
        }
    }
    private static String line(InputStream in) throws IOException {
        ByteArrayOutputStream out=new ByteArrayOutputStream();int c;
        while((c=in.read())!=-1 && c!='\n') {
            if(c!='\r')out.write(c);
            if(out.size()>32768)throw new IOException("HTTP header too long");
        }
        return out.toString("UTF-8");
    }
    private void handle(Socket client) {
        try(Socket socket=client) {
            socket.setSoTimeout(15000);
            InputStream in=new BufferedInputStream(socket.getInputStream());
            String request=line(in);String[] parts=request.split(" ",3);
            if(parts.length<2)return;
            String rawPath=parts[1];String path=rawPath.split("\\?",2)[0];int length=0;
            while(true) {
                String header=line(in);if(header.isEmpty())break;
                if(header.toLowerCase(Locale.ROOT).startsWith("content-length:"))length=Integer.parseInt(header.substring(15).trim());
            }
            if(length<0 || length>1048576)throw new IOException("Unexpected body size");
            byte[] body=new byte[length];int got=0,n;
            while(got<length && (n=in.read(body,got,length-got))>0)got+=n;
            JSONObject event=new JSONObject();event.put("method",parts[0]);event.put("path",rawPath);event.put("body",new String(body,0,got,StandardCharsets.UTF_8));
            record("request",event.toString());
            Map<String,String> args=new HashMap<String,String>();
            String form=new String(body,0,got,StandardCharsets.UTF_8);
            for(String pair:form.split("&")){
                String[] kv=pair.split("=",2);
                if(kv.length==2)args.put(URLDecoder.decode(kv[0],"UTF-8"),URLDecoder.decode(kv[1],"UTF-8"));
            }
            JSONObject all=responses();JSONObject response=all.optJSONObject(path);
            // Combat fixtures are selected by the requested encounter, never globally replaced.
            if(path.startsWith("/combat/") && args.containsKey("instanceid")){
                JSONObject encounter=all.optJSONObject(localSave.fixtureKey(path,args));
                if(encounter==null)encounter=all.optJSONObject(path+"#"+args.get("instanceid"));
                if(encounter!=null)response=encounter;
            }
            if(response==null && path.endsWith(".env"))response=all.optJSONObject("*.env");
            if(response==null && path.endsWith(".mapping"))response=all.optJSONObject("*.mapping");
            int code=response==null?501:response.optInt("status",200);
            String contentType=response==null?"text/plain; charset=utf-8":response.optString("type","application/octet-stream");
            byte[] content;
            try{
                if(response==null)content=("Offline endpoint pending: "+path).getBytes(StandardCharsets.UTF_8);
                else if(response.has("base64"))content=android.util.Base64.decode(response.getString("base64"),android.util.Base64.DEFAULT);
                else content=response.optString("body","").getBytes(StandardCharsets.UTF_8);
                if(code==200 && response!=null && response.has("base64"))content=localSave.respond(path,args,content,all.optJSONObject("_catalog"));
            }catch(Exception e){
                record("request_error",Log.getStackTraceString(e));
                ProtoWire fallback=new ProtoWire();
                if(path.startsWith("/draw/")||path.equals("/guide/draw")){
                    for(int i=0;i<10;i++)fallback.add(1,new ProtoWire().set(1,3).set(2,40330006L).set(4,1).bytes());
                }else fallback.text(1,"ok");
                content=fallback.bytes();code=200;contentType="application/octet-stream";
            }
            OutputStream out=socket.getOutputStream();
            out.write(("HTTP/1.1 "+code+(code==200?" OK":" Pending")+"\r\nContent-Type: "+contentType+"\r\nContent-Length: "+content.length+"\r\nConnection: close\r\nCache-Control: no-store\r\n\r\n").getBytes(StandardCharsets.US_ASCII));
            out.write(content);out.flush();record("response",path+" "+code+" "+content.length);
        } catch(Exception e){record("request_error",Log.getStackTraceString(e));}
    }
    private synchronized void record(String kind,String detail) {
        Log.i(TAG,kind+" "+detail);
        try {
            JSONObject e=new JSONObject();e.put("time",System.currentTimeMillis());e.put("kind",kind);e.put("detail",detail);
            try(FileOutputStream out=new FileOutputStream(new File(getFilesDir(),"offline_http.jsonl"),true)) {
                out.write((e.toString()+"\n").getBytes(StandardCharsets.UTF_8));
            }
        } catch(Exception ignored){}
    }
}
