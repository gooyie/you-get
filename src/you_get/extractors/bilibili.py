#!/usr/bin/env python

__all__ = ['bilibili_download']

from ..common import *

from .sina import sina_download_by_vid
from .tudou import tudou_download_by_id
from .youku import youku_download_by_vid

import hashlib
import re

appkey = 'f3bb208b3d081dc8'
SECRETKEY_MINILOADER = '1c15888dc316e05a15fdd0a02ed6584f'


def get_srt_xml(cid):
    url = 'http://comment.bilibili.com/{cid}.xml'.format(cid = cid)
    return get_content(url)


def parse_srt_p(p):
    fields = p.split(',')
    assert len(fields) == 8, fields
    time, mode, font_size, font_color, pub_time, pool, user_id, history = fields
    time = float(time)

    mode = int(mode)
    assert 1 <= mode <= 8
    # mode 1~3: scrolling
    # mode 4: bottom
    # mode 5: top
    # mode 6: reverse?
    # mode 7: position
    # mode 8: advanced

    pool = int(pool)
    assert 0 <= pool <= 2
    # pool 0: normal
    # pool 1: srt
    # pool 2: special?

    font_size = int(font_size)

    font_color = '#%06x' % int(font_color)

    return pool, mode, font_size, font_color


def parse_srt_xml(xml):
    d = re.findall(r'<d p="([^"]+)">(.*)</d>', xml)
    for x, y in d:
        p = parse_srt_p(x)
    raise NotImplementedError()


def parse_cid_playurl(xml):
    from xml.dom.minidom import parseString
    try:
        doc = parseString(xml.encode('utf-8'))
        urls = [durl.getElementsByTagName('url')[0].firstChild.nodeValue for durl in doc.getElementsByTagName('durl')]
        return urls
    except:
        return []


def bilibili_download_by_cids(cids, title, output_dir='.', merge=True, info_only=False):
    urls = []
    for cid in cids:
        sign_this = hashlib.md5(bytes('cid={cid}&from=miniplay&player=1{SECRETKEY_MINILOADER}'.format(cid = cid, SECRETKEY_MINILOADER = SECRETKEY_MINILOADER), 'utf-8')).hexdigest()
        url = 'http://interface.bilibili.com/playurl?&cid=' + cid + '&from=miniplay&player=1' + '&sign=' + sign_this
        urls += [i
                 if not re.match(r'.*\.qqvideo\.tc\.qq\.com', i)
                 else re.sub(r'.*\.qqvideo\.tc\.qq\.com', 'http://vsrc.store.qq.com', i)
                 for i in parse_cid_playurl(get_content(url))]

    type_ = ''
    size = 0
    for url in urls:
        _, type_, temp = url_info(url)
        size += temp

    print_info(site_info, title, type_, size)
    if not info_only:
        download_urls(urls, title, type_, total_size=None, output_dir=output_dir, merge=merge)


def bilibili_download_by_cid(cid, title, output_dir='.', merge=True, info_only=False):
    while True:
        try:
            sign_this = hashlib.md5(bytes('cid={cid}&from=miniplay&player=1{SECRETKEY_MINILOADER}'.format(cid = cid, SECRETKEY_MINILOADER = SECRETKEY_MINILOADER), 'utf-8')).hexdigest()
            url = 'http://interface.bilibili.com/playurl?&cid=' + cid + '&from=miniplay&player=1' + '&sign=' + sign_this
            urls = [i
                    if not re.match(r'.*\.qqvideo\.tc\.qq\.com', i)
                    else re.sub(r'.*\.qqvideo\.tc\.qq\.com', 'http://vsrc.store.qq.com', i)
                    for i in parse_cid_playurl(get_content(url))]

            type_ = ''
            size = 0
            for url in urls:
                _, type_, temp = url_info(url)
                size += temp or 0

            print_info(site_info, title, type_, size)
            if not info_only:
                download_urls(urls, title, type_, total_size=None, output_dir=output_dir, merge=merge, timeout=1)
        except socket.timeout:
            continue
        else:
            break


def bilibili_live_download_by_cid(cid, title, output_dir='.', merge=True, info_only=False):
    api_url = 'http://live.bilibili.com/api/playurl?cid=' + cid
    urls = parse_cid_playurl(get_content(api_url))

    for url in urls:
        _, type_, _ = url_info(url)
        size = 0
        print_info(site_info, title, type_, size)
        if not info_only:
            download_urls([url], title, type_, total_size=None, output_dir=output_dir, merge=merge)


def bilibili_download_srt_by_cid(cid, title, output_dir, info_only, **kwargs):
    if not info_only and not dry_run:
        if not kwargs['caption']:
            print('Skipping danmaku.')
            return
        title = get_filename(title)
        print('Downloading {title}.cmt.xml ...\n'.format(title=title))
        xml = get_srt_xml(cid)
        with open(os.path.join(output_dir, title + '.cmt.xml'), 'w', encoding='utf-8') as x:
            x.write(xml)


def is_bangumi_play_page(url):
    return re.match(r'https?://bangumi\.bilibili\.com/anime/\d+/play#\d+', url) is not None


def is_bangumi_list_page(url):
    return re.match(r'https?://bangumi\.bilibili\.com/anime/\d+$', url) is not None

def is_video_play_page(url):
    return re.match(r'https?://www\.bilibili\.com/video/av\d+', url) is not None


def is_movie_play_page(url):
    return re.match(r'https?://bangumi\.bilibili\.com/movie/\d+$', url) is not None


def is_live_page(url):
    return re.match(r'https?://live\.bilibili\.com/\d+$', url) is not None


def obtain_episode_id_from_url(url):
    return match1(url, r'play#(\d+)')


def obtain_season_id_from_url(url):
    return match1(url, r'anime/(\d+)')


def get_cid_by_episode_id(episode_id):
    cont = post_content('http://bangumi.bilibili.com/web_api/get_source',
                        post_data={'episode_id': episode_id})
    jsondict = json.loads(cont)
    assert jsondict['code'] == 0 and jsondict['message'] == 'success'
    cid = jsondict['result']['cid']
    return str(cid)


def get_season_info_by_season_id(season_id):
    url = 'http://bangumi.bilibili.com/jsonp/seasoninfo/{season_id}.ver'.format(season_id = season_id)
    cont  = get_content(url)
    jsonstr = match1(cont, r'^[^\{]*(\{.*\})[^\}]*$')
    assert jsonstr
    jsondict = json.loads(jsonstr)
    assert jsondict['code'] == 0 and jsondict['message'] == 'success'
    return jsondict['result']


def obtain_title_in_season_info(seasoninfo, episode_id):
    for episode in seasoninfo['episodes']:
        if episode['episode_id'] == episode_id:
            title = '{title}：第{index}话 {index_title}'.format(
                title = seasoninfo['title'],
                index = episode['index'],
                index_title = episode['index_title'])
            return title


def find_id_in_html(html):
    mo = re.search(r'(cid|ROOMID|vid|ykid|uid)\s*[=:]\s*["\']?(\d+)', html)
    assert mo
    return (mo.group(1), mo.group(2))


def find_title_in_html(html):
    title = r1_of([r'wb_title\s*=\s*["\'](.*?)["\']',
                   r'<h1[^<>]*?>\s*([^<>_-]+)\s*',
                   r'<title>\s*([^_-]+)\s*'], html)
    assert title
    title = unicodize(title)
    title = unescape_html(title)
    title = escape_file_path(title)
    return title


def bilibili_download(url, output_dir='.', merge=True, info_only=False, **kwargs):
    html = get_content(url)
    title = find_title_in_html(html)

    if is_bangumi_play_page(url):
        episode_id = obtain_episode_id_from_url(url)
        season_id = obtain_season_id_from_url(url)
        seasoninfo = get_season_info_by_season_id(season_id)
        title = obtain_title_in_season_info(seasoninfo, episode_id)
        cid = get_cid_by_episode_id(episode_id)
        bilibili_download_by_cid(cid, title, output_dir=output_dir, merge=merge, info_only=info_only)

    elif is_bangumi_list_page(url):
        season_id = obtain_season_id_from_url(url)
        seasoninfo = get_season_info_by_season_id(season_id)
        episodes = seasoninfo['episodes']
        episodes.sort(key = lambda e: float(e['index']))
        for episode in episodes: # download one by one
            title = '{title}：第{index}话 {index_title}'.format(
                title = seasoninfo['title'],
                index = episode['index'],
                index_title = episode['index_title'])
            cid = get_cid_by_episode_id(episode['episode_id'])
            bilibili_download_by_cid(cid, title, output_dir=output_dir, merge=merge, info_only=info_only)
            bilibili_download_srt_by_cid(cid, title, output_dir=output_dir, info_only=info_only, **kwargs)
        return

    elif is_live_page(url):
        t, cid = find_id_in_html(html)
        assert t == 'ROOMID'
        bilibili_live_download_by_cid(cid, title, output_dir=output_dir, merge=merge, info_only=info_only)

    elif is_video_play_page(url) or is_movie_play_page(url):
        t , cid = find_id_in_html(html)
        if t == 'cid':
            options = re.findall(r'<option value=\'(.*)\'[^<>]*>(.*)</option>', html)
            if options: # multi-P
                if re.search(r'index_\d+\.html$', url): # only download one
                    subtitle = dict(options)[match1(url, r'(/video/av\d+/index_\d+\.html)')]
                    title = re.sub(r'\(\d+\)$', '', title)
                    better_title = '{title}：{subtitle}'.format(title=title, subtitle=subtitle) # Build Better Title
                    bilibili_download_by_cid(cid, better_title, output_dir=output_dir, merge=merge, info_only=info_only)
                else:
                    for uri, subtitle in options: # download one by one
                        html = get_content('http://www.bilibili.com{uri}'.format(uri = uri))
                        t, cid = find_id_in_html(html)
                        title = find_title_in_html(html)
                        title = re.sub(r'\(\d+\)$', '', title)
                        better_title = '{title}：{subtitle}'.format(title=title, subtitle=subtitle) # Build Better Title
                        bilibili_download_by_cid(cid, better_title, output_dir=output_dir, merge=merge, info_only=info_only)
                        bilibili_download_srt_by_cid(cid, title, output_dir=output_dir, info_only=info_only, **kwargs)
                    return
            else: # non multi-P
                bilibili_download_by_cid(cid, title, output_dir=output_dir, merge=merge, info_only=info_only)
        elif t == 'vid':
            sina_download_by_vid(cid, title=title, output_dir=output_dir, merge=merge, info_only=info_only)
        elif t == 'ykid':
            youku_download_by_vid(cid, title=title, output_dir=output_dir, merge=merge, info_only=info_only)
        elif t == 'uid':
            tudou_download_by_id(cid, title, output_dir=output_dir, merge=merge, info_only=info_only)
        else:
            raise NotImplementedError('Unsupported Type: {type}'.format(type=t))

    else:
        raise NotImplementedError('Unsupported URL: {url}'.format(url=url))

    bilibili_download_srt_by_cid(cid, title, output_dir=output_dir, info_only=info_only, **kwargs)


site_info = "bilibili.com"
download = bilibili_download
download_playlist = bilibili_download
