package com.codex.witchweapon;

import java.io.*;
import java.util.*;
import java.nio.charset.StandardCharsets;

/** Small protobuf wire editor: preserves fields that this local service does not alter. */
final class ProtoWire {
    static final class Field {
        final int number, type;
        long value;
        byte[] data;
        Field(int n,int t){number=n;type=t;}
    }
    final List<Field> fields=new ArrayList<Field>();
    private static long varint(byte[] b,int[] p) throws IOException {
        long v=0;
        for(int s=0;s<64;s+=7){
            if(p[0]>=b.length)throw new IOException("Truncated protobuf varint");
            int c=b[p[0]++]&255;v|=(long)(c&127)<<s;
            if((c&128)==0)return v;
        }
        throw new IOException("Invalid protobuf varint");
    }
    static ProtoWire parse(byte[] b) throws IOException {
        ProtoWire m=new ProtoWire();int[] p={0};
        while(p[0]<b.length){
            long tag=varint(b,p);Field f=new Field((int)(tag>>>3),(int)(tag&7));
            if(f.number<=0)throw new IOException("Invalid protobuf tag");
            if(f.type==0)f.value=varint(b,p);
            else {
                long length=f.type==2?varint(b,p):f.type==1?8:f.type==5?4:-1;
                if(length<0 || length>b.length-p[0])throw new IOException("Invalid protobuf field length");
                f.data=Arrays.copyOfRange(b,p[0],p[0]+(int)length);p[0]+=(int)length;
            }
            m.fields.add(f);
        }
        return m;
    }
    private static void varint(ByteArrayOutputStream o,long v){
        while((v&~127L)!=0){o.write((int)(v&127)|128);v>>>=7;}o.write((int)v);
    }
    byte[] bytes(){
        ByteArrayOutputStream o=new ByteArrayOutputStream();
        for(Field f:fields){
            varint(o,((long)f.number<<3)|f.type);
            if(f.type==0)varint(o,f.value);
            else {if(f.type==2)varint(o,f.data.length);o.write(f.data,0,f.data.length);}
        }
        return o.toByteArray();
    }
    ProtoWire clear(int n){for(Iterator<Field> i=fields.iterator();i.hasNext();)if(i.next().number==n)i.remove();return this;}
    ProtoWire add(int n,long v){Field f=new Field(n,0);f.value=v;fields.add(f);return this;}
    ProtoWire add(int n,byte[] v){Field f=new Field(n,2);f.data=v;fields.add(f);return this;}
    ProtoWire set(int n,long v){return clear(n).add(n,v);}
    ProtoWire set(int n,byte[] v){return clear(n).add(n,v);}
    ProtoWire text(int n,String v){return set(n,v.getBytes(StandardCharsets.UTF_8));}
    long number(int n,long fallback){for(Field f:fields)if(f.number==n&&f.type==0)return f.value;return fallback;}
    byte[] data(int n){for(Field f:fields)if(f.number==n&&f.type==2)return f.data;return new byte[0];}
    List<Long> integers(int n)throws IOException{
        List<Long> out=new ArrayList<Long>();
        for(Field f:fields)if(f.number==n){
            if(f.type==0)out.add(f.value);
            else if(f.type==2){int[] pos={0};while(pos[0]<f.data.length)out.add(varint(f.data,pos));}
        }
        return out;
    }
    double[] doubles(int n){
        ArrayList<Double> values=new ArrayList<Double>();
        for(Field f:fields)if(f.number==n&&(f.type==1||f.type==2)){
            java.nio.ByteBuffer b=java.nio.ByteBuffer.wrap(f.data).order(java.nio.ByteOrder.LITTLE_ENDIAN);
            while(b.remaining()>=8)values.add(b.getDouble());
        }
        double[] out=new double[values.size()];for(int i=0;i<out.length;i++)out[i]=values.get(i);return out;
    }
    ProtoWire doubles(int n,double[] values){
        java.nio.ByteBuffer b=java.nio.ByteBuffer.allocate(values.length*8).order(java.nio.ByteOrder.LITTLE_ENDIAN);
        for(double v:values)b.putDouble(v);return set(n,b.array());
    }
}
