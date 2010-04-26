#!/usr/bin/python
# -*- encoding: utf-8 -*-
#
# Chmouel Boudjnah <chmouel@chmouel.com>
import re
import urllib2
import htmlentitydefs

from BeautifulSoup import BeautifulStoneSoup

class PostCodeError(Exception): pass
class InvalidRouteNumber(Exception): pass

def descape_entity(m, defs=htmlentitydefs.entitydefs):
    try:
        return defs[m.group(1)]
    except KeyError:
        return m.group(0) # use as is

def descape(string):
    html_entitity_pattern = re.compile("&(\w+?);")
    return html_entitity_pattern.sub(descape_entity, string)

def get_route(html):
    # f = open("/tmp/a.html", 'w')
    # f.write(html.read())
    # f.close
    # sys.exit()
    soup = BeautifulStoneSoup(html)
    re_time=re.compile('^<td class="(start|interchange)">([^\<]+)<br>.*alt="([^"]*?)" hspace="\d+"></img><br></br>(\d+:\d+)')
    re_description=re.compile('^<td>([^<]+)<br><\/br>(.*)<br></br>(<br></br>)?.*')
    re_duration=re.compile('^\<td class="jpinformation" width="90"><ul><li>(Transfer|Average journey) time: (\d+)')
    re_uk_postcode=re.compile('^([A-PR-UWYZ0-9][A-HK-Y0-9][AEHMNPRTVXY0-9]?[ABEHMNPRVWXY0-9]? {1,2}[0-9][ABD-HJLN-UW-Z]{2}|GIR 0AA)$')
    
    def fix_html(value):
        ret = re.sub(r'<[^>]*?>', ' ', value)
        ret = ret.replace(' ', '')
        return descape(re.sub(r'\s{2,}', ' ', ret))

    ret=[]
    end_description=None
    for tr in soup.find('table').findAll('tr'):
        if not tr.td:
            continue
        dico={}
        tds = tr.findAll('td')
        if len(tds)  < 4:
            raise PostCodeError
        s_time = str(tds[0]).replace('\n', '').strip()
        description = str(tds[1]).replace('\n', ' ').strip()
        duration = str(tds[2]).replace('\n', '').strip()

        _d = fix_html(description).strip()
        if re_uk_postcode.match(_d):
            pass
        else:
            end_description = fix_html(description)
            
        #print s_time
        match_time = re_time.match(s_time)
        if 'class="end"' in s_time:
            dico['time_end'] = s_time.replace('<td class="end">', '').replace("</td>", "")
            dico['description'] = end_description
            ret.append(dico)
            continue
        elif match_time:
            d = match_time.group(2)
            end_time =  match_time.group(4)
            if d == ' ':
                d = None
            if end_time == ' ':
                end_time = None
            dico['time_start'] =  d
            dico['time_end'] =  end_time
            route_type = match_time.group(3)
            if route_type == 'Walk':
                route_type = 'Walking'
            dico['route_type'] = route_type
        else:
            continue

        match_description = re_description.match(description)
        if match_description:
            dico['from'] = descape(match_description.group(1))
            desc = match_description.group(2)
            if "routealert_" in desc:
                dico['notice'] = re.sub(r'.*?<span class="routealert_(green|blue|red)">([^\<]*).*', r'\2', desc)
                dico['description'] = fix_html(re.sub(r'^(.*)<br></br><br></br>.*', r'\1', desc))
            else:
                dico['description'] = fix_html(match_description.group(2))
        else:
            continue

        match_duration = re_duration.match(duration)
        if match_duration:
            dico['duration'] = match_duration.group(2)
        else:
            continue

        ret.append(dico)
    return ret
        
#TODO: with time
def get_journeys(z_origin, z_destination, route=0):
    regex = re.compile('.*</td><td class="depart">(?P<depart>[^<]*)</td><td class="arrive">(?P<arrive>[^<]*)</td><td class="duration">(?P<duration>[^<]*)</td>.*?<a href="(?P<url>XSLT*[^"]*).*')
    url="http://journeyplanner.tfl.gov.uk/user/XSLT_TRIP_REQUEST2?language=en&sessionID=0&type_destination=locator&name_destination=%(destination)s&type_origin=locator&name_origin=%(origin)s&place_origin=London&place_destination=London"
    req = urllib2.Request(url % ({ "origin" : z_origin.replace(" ", ""), "destination" : z_destination.replace(" ", "") }))
    urlhandle = urllib2.urlopen(req)
    cookie = urlhandle.headers['Set-Cookie']
    # urlhandle = open("/tmp/x.html", 'r')
    results=[]

    route_cnt = 1
    for line in urlhandle:
        if not '<tr><th>Route</th><th>' in line:
            continue

        for split in line.split('<td class="option">')[1:]:
            match = regex.match(split)
            if match:
                results.append({
                        'depart' : match.group('depart'),
                        'arrive' : match.group('arrive'),
                        'duration' : match.group('duration'),
                        'url' : match.group('url'),
                        'route_id' : route_cnt
                        })
                route_cnt += 1
                
    urlhandle.close()

    if route == 0:
        return results

    if route > len(results):
        raise InvalidRouteNumber

    for res in results:
        if res['route_id'] != route:
            continue
        url = "http://journeyplanner.tfl.gov.uk/user/%s" % (res['url'].replace('&amp;', '&'))
        req = urllib2.Request(url)
        req.add_header('Set-Cookie', cookie)
        r = urllib2.urlopen(req)
        return get_route(r)


if __name__ == '__main__':
    origin_zipcode = "W13 8PH"
    destination_zipcode = "UB 111ET"
    results = get_journeys(origin_zipcode, destination_zipcode)
    # html = open("/tmp/a.html", 'r')
    # results = get_route(html)
    from pprint import pprint as p
    p(results)
