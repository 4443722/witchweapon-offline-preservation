from offline_story import audit
if __name__=='__main__':
 entries,_=audit()
 print('Entries:',len(entries),'complete:',sum(x['playable'] for x in entries),'missing lesson:',sum(not x['lesson_present'] for x in entries),'missing cut dependencies:',sum(bool(x['missing_dependencies']) for x in entries))
