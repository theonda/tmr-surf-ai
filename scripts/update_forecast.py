import json,datetime,urllib.parse,urllib.request,pathlib,re,time
from concurrent.futures import ThreadPoolExecutor,as_completed
ROOT=pathlib.Path(__file__).resolve().parents[1]
html=(ROOT/'index.html').read_text()
SPOTS=[dict(id=m.group(1),lat=float(m.group(2)),lon=float(m.group(3))) for m in re.finditer(r"\{id:'([^']+)',name:'[^']+',lat:([\d.]+),lon:([\d.]+)",html)]
def api(url,params):
    address=url+'?'+urllib.parse.urlencode(params)
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(address,headers={'User-Agent':'TMR-SURF-AI/0.3'}),timeout=35) as resp:return json.load(resp)
        except Exception:
            if i==2:raise
            time.sleep(2*(i+1))
def get(s):
    base={'latitude':s['lat'],'longitude':s['lon'],'timezone':'Asia/Tokyo','forecast_days':7}
    m=api('https://marine-api.open-meteo.com/v1/marine',{**base,'hourly':'wave_height,wave_direction,wave_period,swell_wave_height,swell_wave_period','cell_selection':'sea'})['hourly']
    w=api('https://api.open-meteo.com/v1/forecast',{**base,'hourly':'wind_speed_10m,wind_direction_10m','wind_speed_unit':'ms'})['hourly']
    idx={t:i for i,t in enumerate(w['time'])}
    rows=[]
    for i,t in enumerate(m['time']):
        j=idx.get(t)
        if j is not None:rows.append({'t':t,'h':m['wave_height'][i],'dir':m['wave_direction'][i],'p':m['wave_period'][i],'sh':m['swell_wave_height'][i],'sp':m['swell_wave_period'][i],'w':w['wind_speed_10m'][j],'wd':w['wind_direction_10m'][j]})
    return s['id'],rows
if __name__=='__main__':
    all={}
    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs={pool.submit(get,s):s for s in SPOTS}
        for job in as_completed(jobs):
            k,rows=job.result()
            if not rows:raise RuntimeError('No data for '+k)
            all[k]=rows
    if len(all)!=len(SPOTS):raise RuntimeError('Incomplete results '+str(len(all)))
    output=ROOT/'data/latest.json';output.parent.mkdir(exist_ok=True)
    temp=output.with_suffix('.tmp');temp.write_text(json.dumps({'fetchedAt':int(datetime.datetime.now(datetime.timezone.utc).timestamp()*1000),'all':all},ensure_ascii=False,separators=(',',':')));temp.replace(output)
    print('Updated',len(all),'spots')