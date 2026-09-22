"""Generate a temporary in-process Lua call for one recovered static parser."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
route,cls=sys.argv[1:3]
base=json.loads((ROOT/'offline_responses.json').read_text('utf8'))[route]['base64']
code="""require 'tolua.reflection'
tolua.loadassembly('Assembly-CSharp')
local F=bit.bor(4,8,16,32)
local convert=tolua.gettypemethod(typeof('System.Convert'),'FromBase64String',F,System.Type.DefaultBinder,{typeof('System.String')},nil)
local data=convert:Call('%s');convert:Destroy()
local parse=tolua.gettypemethod(typeof('%s'),'ParseProtoBuf',F,System.Type.DefaultBinder,{typeof('System.Byte[]')},nil)
parse:Call(data);parse:Destroy()
return 'parsed %s'
"""%(base,cls,route)
p=ROOT/'evidence/debug_parse.lua';p.write_text(code,'utf8');print(p)
