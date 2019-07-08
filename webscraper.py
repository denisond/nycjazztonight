import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import re
from functools import reduce
import json

start = datetime.now()
print('SCRAPER STARTING AT: {}'.format(start))

def birdland_scraper():
    r = requests.get('https://www.birdlandjazz.com/calendar/')
    soup = BeautifulSoup(r.text, 'html.parser')
    results_days = soup.select('td[class*="has-event"]')

    records=[]
    for result in results_days:
        result_len = len(result.contents)
        date = result.contents[0].text + ' {}'.format(datetime.now().year)
        for i in range(result_len)[1:]:
            name = result.contents[i].find('h1',{'class':'headliners summary'}).text
            time = result.contents[i].find('h3',{'class':'start-time'}).text
            records.append((date,time,name))

    df = pd.DataFrame(records, columns= ['date', 'time', 'Birdland Jazz Club'])

    df['start_time'] = pd.to_datetime(df['time']).dt.strftime('%I:%M %p')
    df['date'] = pd.to_datetime(df['date'].apply(lambda x: x[3:]))
    df = (df.set_index(['date', 'start_time'])
            .drop('time', axis=1))

    return df


def bluenote_scraper():
    r = requests.get('http://www.bluenotejazz.com/newyork/schedule/printable.shtml')
    soup = BeautifulSoup(r.text, 'html.parser')
    records=[]
    month = datetime.now().month
    for k,v in enumerate(soup.find_all('td',{'class':'show'})):
        if v.find('p'):
            date = soup.find_all('td',{'class':'date'})[k].text
            for show in v.find_all('p'):
                records.append(list((month, date, show.text)))
    records_np = np.array(records)
    month_ary = [month]
    for i in range(len(records_np)-1):
        if int(records_np[i,1]) > int(records_np[i+1,1]):
            month += 1
            month %= 13
            if month ==0:
                month = 1
            month_ary.append(month)
        else:
            month_ary.append(month)
            
    month_date = np.array(list(zip(month_ary,records_np[:,1])))
    records_np[:,:2] = month_date

    df = pd.DataFrame(records_np, columns = ['month', 'day', 'showtime'])
    df['start_time'] = pd.to_datetime(df['showtime'].apply(lambda x: '{}'.format(re.findall(r'\d{1,2}:\d{2}.M',x))[2:-2])).dt.strftime('%I:%M %p')
    df['Bluenote'] = df['showtime'].apply(lambda x: re.sub('\d{1,2}:\d{2}.M','',x))
    df['date'] = pd.to_datetime(str(datetime.today().year) + '-' +(df['month'].apply(lambda x: str(x))) + '-' + df['day'], format = '%Y-%m-%d')

    df = (df.set_index(['date','start_time'])
            .drop(['showtime', 'month','day'], axis=1))

    return df


def dizzys_scraper():
    r = requests.get('https://www.jazz.org/dizzys/')
    soup = BeautifulSoup(r.text, 'html.parser')
    main = soup.find('div', {'class':'container container-md-height'})
    shows = main.find_all('div',{'class':'col-sm-4 col-md-height feature-hover-container'})
    records=[]
    for show in shows:
        artist = show.find('span',{'class':'overlay'}).text
        for time in show.find_all('option'):
            date_time = time.text
            records.append((date_time, artist))

    df = pd.DataFrame(records, columns = ['datetime', 'Dizzy\'s'])
    df['date'] = pd.to_datetime(df['datetime'] + ' ' + str(datetime.now().year)).dt.date
    df['start_time'] = pd.to_datetime(df['datetime'] + ' ' + str(datetime.now().year)).dt.strftime('%I:%M %p')
    df = df.sort_values(['date','start_time'])
    df = (df.set_index(['date','start_time'])
            .drop(['datetime'], axis=1))
            
    return df


def django_scraper():
    r = requests.get('http://www.thedjangonyc.com/schedule/')
    soup = BeautifulSoup(r.text, 'html.parser')
    main = soup.find_all('div', {'class':"day" })
    records = []
    for i in main:
        date = i.find('div',{'class':'day-name'}).text
        for j in i.find_all('div',{'class':'event'}):
            event = j.find('div',{'class':'event-title'}).text
            if len(event) > 1: # So we don't include events that are empty st strings  
                records.append((date, event))
    df = pd.DataFrame(records, columns = ['date', 'event_time'])

    df['date'] = pd.to_datetime(df['date'].apply(lambda x: x.split(' ',1)[1] + ', {}'.format(datetime.now().year)))


    df['event_time2'] = df['event_time'].apply(lambda x: '{}'.format(re.findall('(\d*:?\d+?\s*[ap]m)',x.lower())[0]) if len(re.findall('(\d*:?\d+?\s*[ap]m)',x.lower())) > 0 else None)
    df.dropna(inplace= True)
    df['start_time'] = pd.to_datetime(df['event_time2'].apply(lambda x: (re.findall('\d+',x)[0] + ':00' + x[-2:]).replace(" ", "") if not ":" in x else x.replace(" ", ""))).dt.strftime('%I:%M %p')
    df['Django'] = df['event_time'].apply(lambda x: re.sub('(\d*:?\d+?\s*[AP]M)','',x,flags=re.IGNORECASE))
    df = (df.set_index(['date','start_time'])
            .drop(['event_time', 'event_time2'], axis=1))

    return df


def fatcat_scraper():
    r = requests.get('http://www.fatcatmusic.org/music1.html')
    soup = BeautifulSoup(r.text, 'html.parser')


    dates_fc = [result.text for result in soup.find_all('table',{'width':'100%'})[0].find_all('td',{'class':'date'})]
    times_fc   = [result.text for result in soup.find_all('table',{'width':'100%'})[0].find_all('td',{'class':'bodycopy'})[::2]]
    artists_fc = [result.text for result in soup.find_all('table',{'width':'100%'})[0].find_all('td',{'class':'bodycopy'})[1::2]]

    dates_clean_fc = sorted(list(map(lambda x: re.findall('\d+\/\d+',x)[0],dates_fc*3)))

    records=list(zip(dates_clean_fc, times_fc, artists_fc))

    df = pd.DataFrame(records, columns = ['date', 'time', 'Fat Cat'])
    df['start_time'] = pd.to_datetime(df['time'].apply(lambda x: (re.findall('\d+',x)[0] + ':00' + x[-2:]).replace(" ", "") if not ":" in x else x.replace(" ", ""))).dt.strftime('%I:%M %p')
    df['date'] = pd.to_datetime(df['date'] + '/{}'.format(datetime.now().year))
    df = (df.set_index(['date','start_time'])
            .drop('time', axis=1))

    return df

def jazzgallery_scraper():
    r = requests.get('https://www.etix.com/ticket/v/3525/the-jazz-gallery')
    soup = BeautifulSoup(r.text, 'html.parser')
    main = soup.find('div', {'id':'view','class':'sixteen columns'})
    shows = main.find_all('div', {'class':'row performance show-divider'})
    records = []
    for show in shows:
        date = '{} {}'.format(show.find('span',{'class':'month'}).text, show.find('span',{'class':'date'}).text)
        time = show.find('div',{'class':'performance-datetime'}).text
        artist = show.find('h4',{'class':'performance-name'}).find('a').text
        records.append((date, time, artist))

    df = pd.DataFrame(records, columns = ['date_temp','time_temp', 'Jazz Gallery'])
    df['start_time'] = pd.to_datetime(df['time_temp'].apply(lambda x: ' '.join(x.split(' ', -1)[-2:]))).dt.strftime('%I:%M %p')
    df['date'] = pd.to_datetime(df['date_temp'] + ' ' + str(datetime.now().year))

    df = df.sort_values(['date','start_time'])
    df = (df.set_index(['date','start_time'])
            .drop(['time_temp','date_temp'], axis=1))

    return df

def jazzstandard_scraper():
    r = requests.get('https://www.ticketweb.com/venue/jazz-standard-new-york-ny/19760')
    soup = BeautifulSoup(r.text, 'html.parser')
    main = soup.find('div',{'class':'section-body'})
    events = main.find_all('li', {'class':'media theme-mod'})
    records = []
    for i in events:
        event = i.find('p',{'class':'event-name theme-title'}).find('a').text
        time = i.find('p',{'class':'event-date theme-subTitle'}).text[25:-20]
        records.append((time,event))
    df= pd.DataFrame(records,columns = ['datetime','Jazz Standard'])
    df['start_time'] = pd.to_datetime(df.datetime.apply(lambda x: x[3:].rsplit('\n',1)[0]).apply(lambda x: x.rsplit('(',1)[0])+ ', {}'.format(datetime.now().year)).dt.strftime('%I:%M %p')
    df['date'] = pd.to_datetime(df.datetime.apply(lambda x: x[3:].rsplit('\n',1)[0]).apply(lambda x: x.rsplit('(',1)[0])+ ', {}'.format(datetime.now().year)).apply(lambda x: x.date())
    df = (df.set_index(['date','start_time'])
            .drop(['datetime'], axis=1))

    return df

def kitano_scraper():
    r = requests.get('https://www.instantseats.com/index.cfm?fuseaction=home.venue&VenueID=147')
    soup = BeautifulSoup(r.text, 'html.parser')
    main = soup.find('div',{'class': 'event-list'})
    shows = main.find_all('div',{'class': 'row'})
    records = []
    for show in shows:
        date = show.find('p',{'id':'event-date'}).text
        artist = show.find('h1',{'id':'event-title'}).text
        time = show.find('p',{'id':'event-time'}).text
        records.append((date,time, artist))
    records

    df = pd.DataFrame(records, columns = ['date', 'time', 'Kitano'])
    df['date'] = pd.to_datetime(df['date'].apply(lambda x: x.replace('.', "/")) + '/'+ '{}'.format(datetime.now().year))
    df['start_time'] = pd.to_datetime(df['time']).dt.strftime('%I:%M %p')
    df = (df.set_index(['date','start_time'])
            .drop(['time'], axis=1))

    return df


def mezzrow_scraper():
    r = requests.get('https://www.mezzrow.com/')
    soup = BeautifulSoup(r.text, 'html.parser')
    main = soup.find_all('dl')[0]
    results = main.find_all(['dd','dt'])
    records = []
    date = ''
    time = ''
    event = ''
    for k,i in enumerate(results):
        if 'class="purple"' in str(i):
            date = i.text
        if 'class="orange event' in str(i):
            time = i.text
        if 'class="event"' in str(i):
            event = i.find('a').text
            records.append((date, time, event))

    df = pd.DataFrame(records, columns = ['date', 'time', 'Mezzrow'])        
    df['start_time'] = pd.to_datetime(df['time'].apply(lambda x: re.findall('(\d*:?\d+?\s*[ap]m)',x.lower())[0])).dt.strftime('%I:%M %p')

    df['date'] = pd.to_datetime(df['date'])
    df = (df.set_index(['date','start_time'])
            .drop('time', axis=1))

    return df

def seventyfive_scraper():
    r = requests.get('https://www.the75clubnyc.com/')
    soup = BeautifulSoup(r.text, 'html.parser')
    main = soup.find('div', {'class':'qode-workflow'})
    shows = main.find_all('div',{'class':'qode-workflow-text'})
    records = []
    for i in shows:
        day = i.find('h4').text.rsplit(' ',-1)[-1]
        name = i.find('h3',{'class':'qode-workflow-subtitle'}).text
        for j in ['08:00 PM', '9:30 PM']:
            time = j
            records.append((day,time,name))

    month = datetime.now().month
    records_np = np.array(records)
    month_ary = [month]
    for i in range(1,len(records_np)):

        if int(records_np[i-1,0]) > 25 and int(records_np[i,0]) < 5:
            month += 1
            month %= 13
            if month ==0:
                month = 1
            month_ary.append(month)
        else:
            month_ary.append(month)

    records3 = np.insert(records_np, 0, month_ary, axis=1)
    df = pd.DataFrame(records3, columns = ['month', 'day', 'time', '75 Club'])
    df['date'] = pd.to_datetime((df['month'] + "/"+ df['day']).apply(lambda x: x + '/'+ '{}'.format(datetime.now().year)))
    df['start_time'] = pd.to_datetime(df['time'].apply(lambda x: (re.findall('\d+',x)[0] + ':00' +  x[-2:]).replace(" ", "") if ":" not in x else x.replace(" ", ""))).dt.strftime('%I:%M %p')
    df = (df.sort_values(['date','start_time']).set_index(['date','start_time'])
        .drop(['month','day','time'], axis=1))

    return df

def smalls_scraper():
    r = requests.get('https://www.smallslive.com/events/calendar/')
    soup = BeautifulSoup(r.text, 'html.parser')
    results_days = soup.select('div[class*="day flex"]') 

    records=[]

    for result in results_days:        
        date = result.contents[0].text 
        for i in range(len(result.find_all('dt'))):
            name = result.find_all('a')[i].text            
            time = result.find_all('dt')[i].text            
            records.append((date,time,name))

    df = pd.DataFrame(records, columns = ['date', 'time', 'Smalls Jazz Club'])

    df['start_time'] = pd.to_datetime(df['time'].apply(lambda x: x[:8])).dt.strftime('%I:%M %p')
    df['date'] = pd.to_datetime(df['date'])

    df = (df.set_index(['date','start_time'])
            .drop('time', axis=1))

    return df


def smoke_scraper():
    r = requests.get('https://www.smokejazz.com/index.php/calendar/')
    soup = BeautifulSoup(r.text, 'html.parser')
    main = soup.find('div',{'class':'calendar'})

    days = main.find_all('div', {'class': 'cal_entries'})

    records = []
    for i in days:
        date = i.find('h5',{'class':'dateHead txt-drk'}).text
        for v in i.find_all('div',{'class':'event_entry tab-pane active'}):
            name = v.find('h3',{'class':'smkHead uppercase'}).text

            times_full_temp = [re.findall('(\d+:\d+\s.m)',p.text.lower()) for p in v.find_all('p') ]
            times_full = list(set([i for i in times_full_temp if i][0]))

            obs = len(times_full)
            dates_full = [date for i in range(obs)]
            names_full = [name for i in range(obs)]
            records.append(list(zip(dates_full, times_full, names_full)))

    records2 = []
    for i in records:
        for j in i:
            records2.append(j)

    df = pd.DataFrame(records2, columns = ['date', 'time', 'Smoke Bar'])
    df['start_time'] = pd.to_datetime(df['time']).dt.strftime('%I:%M %p')
    df['date'] = pd.to_datetime(df['date'])
    df = (df.set_index(['date','start_time'])
            .drop('time', axis=1))

    return df


def villagevanguard_scraper():
    r = requests.get('https://www.squadup.com/api/v3/events?user_ids=4158761&page_size=200&additional_attr=sold_out&include=custom_fields')
    data = json.loads(r.text)

    shows = [i['name'].split('-',1)[1] for i in data['events']]
    date = [i['start_at'].split('T',1)[0] for i in data['events']]
    time = [i['start_at'].split('T',1)[1].split('-',1)[0] for i in data['events']]
    records = list(zip(date,time,shows))
    
    df = pd.DataFrame(records, columns = ['date','time', 'Village Vanguard'])
    df['date'] = pd.to_datetime(df['date'])
    df['start_time'] = pd.to_datetime(df['time']).dt.strftime('%I:%M %p')
    
    df = (df.set_index(['date','start_time'])
            .drop(['time'], axis=1))
    return df


def zinc_scraper():
    r = requests.get('https://zincjazz.com/shows/')
    soup = BeautifulSoup(r.text, 'html.parser')
    main = soup.find_all('div', {'class':"edgtf-row-grid-section-wrapper" })[1]


    days = main.find_all('a', {'class':'edgtf-el-item-link-outer'})

    records = []
    for i in days:
        r = requests.get(i['href'])
        soup = BeautifulSoup(r.text, 'html.parser')
        date = soup.find('span',{'class':"offbeat-event-info-item-desc"}).text
        name = soup.find(['h2','h4']).text

        times_temp = [re.findall('(\d*:?\d+?\s*[ap]m)',i.text.lower()) for i in soup.find_all(['p','h4'])]

        times_full_temp= [val for sublist in times_temp for val in sublist]
        times_full = list(set(times_full_temp))
        obs = len(times_full)

        dates_full = [date for i in range(obs)]
        names_full = [name for i in range(obs)]
        records.append(list(zip(dates_full, times_full, names_full)))
    records2 = []
    for i in records:
        for j in i:
            records2.append(j)

    df = pd.DataFrame(records2, columns = ['date', 'time', 'Zinc Bar'])
    df['start_time'] = pd.to_datetime(df['time'].apply(lambda x: (re.findall('\d+',x)[0] + ':00' +  x[-2:]).replace(" ", "") 
                                                       if ":" not in x else x.replace(" ", ""))).dt.strftime('%I:%M %p')
    df['date'] = pd.to_datetime(df['date'])
    df = (df.set_index(['date','start_time'])
            .drop('time', axis=1))

    return df




"""
Create datasets
"""
scrapers = [birdland_scraper, bluenote_scraper, dizzys_scraper, django_scraper, fatcat_scraper, 
            jazzgallery_scraper, jazzstandard_scraper, kitano_scraper, mezzrow_scraper, 
            seventyfive_scraper, smalls_scraper, smoke_scraper, villagevanguard_scraper, zinc_scraper]
data_frames = []

for scraper in scrapers:
    try:
        data_frames.append(scraper())
    except:
        print('{} CRASHED!'.format(scraper).upper())
        
full_df = reduce(lambda  left,right: pd.merge(left,right,on=['date','start_time'], how='outer'), data_frames).sort_values(['date', 'start_time'])
final_df = full_df.loc[datetime.today() - timedelta(days = 1):]

# filter NaNs
final_df = final_df.astype('object').fillna(" ").iloc[:350]

# added utf-8 encoding to fix write error on ubuntu
final_df.to_csv('schedule.csv', encoding='utf-8')

finish = datetime.now()
print('SCRAPER FINISHED AT: {}'.format(finish))

print('TIME ELAPSED: {}'.format(finish - start))