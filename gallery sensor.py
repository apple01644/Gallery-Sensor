import collections
import io
import random

import bs4
import requests as req

GALL_NAME = "새보수갤"
GALL_ID = 'newconservativeparty'
URL = f'https://gall.dcinside.com/mgallery/board/lists?id={GALL_ID}&list_num=100'
header = {'Host': 'gall.dcinside.com', 'Pragma': 'no-cache',
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0'}
POST_COUNT = 2000
POST_START_PAGE = 3


class UnexpectedStatus:
    pass


class Post:
    def __init__(self):
        self.is_pic = False
        self.is_rcm = False
        self.title = False
        self.pk = 0
        self.view_count = 0
        self.like_count = 0
        self.comment_count = 0

    def is_picture(self, html: bs4.element.Tag):
        self.is_pic = ('icon_pic' in html.attrs['class']) or ('icon_recomimg' in html.attrs['class'])

    def is_recommend(self, html: bs4.element.Tag):
        self.is_pic = ('icon_recomtxt' in html.attrs['class']) or ('icon_recomimg' in html.attrs['class'])

    def __str__(self):
        return ('★' if self.is_rcm else '　') + ('글' if self.is_pic else '　') + '%7s' % (
                '(%3d, %3d, %3d) ' % (self.view_count, self.like_count, self.comment_count)) + self.title

    def __repr__(self):
        return self.__str__()

    def to_json(self):
        return {'is_pic': self.is_pic, 'is_rcm': self.is_rcm, 'title': self.title, 'view_count': self.view_count,
                'like_count': self.like_count, 'comment_count': self.comment_count, 'pk': self.pk}

    @staticmethod
    def from_post(json: dict):
        post = Post()
        post.pk = json['pk']
        post.is_pic = json['is_pic']
        post.is_rcm = json['is_rcm']
        post.title = json['title']
        post.view_count = json['view_count']
        post.like_count = json['like_count']
        post.comment_count = json['comment_count']
        return post


def get_list(post_count=POST_COUNT, page=POST_START_PAGE):
    data = []
    ids = []

    while post_count > len(ids):
        res = req.get(f'{URL}&page={page}', headers=header)
        if res.status_code != 200:
            raise UnexpectedStatus
        content = res.content.decode('utf-8')

        for post_node in bs4.BeautifulSoup(content, features='html.parser').find_all('tr', attrs={'class': 'us-post'}):
            if post_node.find('td', attrs={'class': 'gall_subject'}).text == '일반':
                post_obj = Post()
                icon, title = list(post_node.find('td', attrs={'class': 'gall_tit'}).findChildren()[0])
                post_obj.is_picture(icon)
                post_obj.is_recommend(icon)
                post_obj.title = title
                post_obj.view_count = int(post_node.find('td', attrs={'class': 'gall_count'}).text)
                post_obj.like_count = int(post_node.find('td', attrs={'class': 'gall_recommend'}).text)

                comment_node = post_node.find('span', attrs={'class': 'reply_num'})
                if comment_node:
                    post_obj.comment_count = int(comment_node.text[1:-1])

                the_id = post_node.find('td', attrs={'class': 'gall_num'}).text
                if the_id in ids:
                    continue
                else:
                    ids.append(the_id)
                    post_obj.pk = int(the_id)
                    print(the_id)

                data.append(post_obj.to_json())
        page += 1
    return data


def standard_get_data():
    posts = get_list()
    with io.open('data', 'w', encoding='utf-8') as file:
        file.write(str(posts))


def process_title(title: str, folder: dict):
    org_title = title
    title_length = len(title)

    unrecognized_title = ''
    recognized_title = []
    while title_length > 0:
        for length in folder:
            if length < title_length:
                for word in folder[length]:
                    if word == title[:length]:
                        recognized_title.append(folder[length][word])
                        title = title[len(word):]
                        title_length = len(title)
        if title_length > 0:
            ch = title[0]
            if not (ch == '\f' or ch == '\n' or ch == '\v' or ch == '\t' or ch == '\r'):
                unrecognized_title += ch
            title = title[1:]
            title_length -= 1

    return {'recognized_title': recognized_title, 'unrecognized_title': unrecognized_title, 'org_title': org_title}


def recognize_data(show_unrecognized_data=False):
    posts = []
    folder = {}
    files = ['common', 'countries', 'estate', 'men', 'politics', 'others']

    with io.open('data', 'r', encoding='utf-8') as file:
        for post in eval(file.read()):
            posts.append(Post.from_post(post))

    for filename in files:
        with io.open(f'dict/{filename}.txt', 'r', encoding='utf-8') as file:
            for line in file.read().split('\n'):
                if len(line) > 0:
                    if line[0] != '#':
                        for idea in line.split(','):
                            words = idea.split('|')
                            for word in words:
                                if len(word) > 0:
                                    word = word.replace('&comma;', ',')
                                    if not (len(word) in folder):
                                        folder[len(word)] = {}
                                    folder[len(word)][word] = words[0]
    print(folder)

    titles = []
    for post in posts:
        #post.title = post.title.replace('안철수', '安철水')
        #post.title = post.title.replace('새보', '새/보')
        #post.title = post.title.replace('우한', '우/한')
        #post.title = post.title.replace('한갤', '한/갤')
        titles.append(post.title)

    comment_sorted_list = [k for k in sorted(posts, key=lambda post: post.comment_count, reverse=True)]
    like_sorted_list = [k for k in sorted(posts, key=lambda post: post.like_count, reverse=True)]
    view_sorted_list = [k for k in sorted(posts, key=lambda post: post.view_count, reverse=True)]

    comment_top = comment_sorted_list[:20]
    like_top = like_sorted_list[:20]
    view_top = view_sorted_list[:20]
    view_bot = view_sorted_list[-20:]
    view_bot.reverse()

    print('<span style="color: rgb(0, 0, 0,);">')
    print(
        f'<b><span style="font-size: 14pt;">=== {GALL_NAME}에서 댓글이 제일 많이 달린 게시글 (페이지 {POST_START_PAGE}부터 {POST_COUNT}개의 게시물이 표본) ===</span></b><br>')
    for k, post in enumerate(comment_top):
        print(
            f'<div><a href="/mgallery/board/view/?id={GALL_ID}&no={post.pk}">{k + 1}위</a> (댓글 {"%3d" % post.comment_count}개) {post.title}<br></div>')
    print('<br>')

    print(f'<b><span style="font-size: 14pt;">=== {GALL_NAME}에서 개추가 제일 많이 달린 게시글 ===</span></b><br>')
    for k, post in enumerate(like_top):
        print(
            f'<div><a href="/mgallery/board/view/?id={GALL_ID}&no={post.pk}">{k + 1}위</a> (개추 {"%3d" % post.like_count}개) {post.title}<br></div>')
    print('<br>')

    print(f'<b><span style="font-size: 14pt;">=== {GALL_NAME}에서 조회수가 제일 많은 게시글 ===</span></b><br>')
    for k, post in enumerate(view_top):
        print(
            f'<div><a href="/mgallery/board/view/?id={GALL_ID}&no={post.pk}">{k + 1}위</a> (조회수 {"%3d" % post.view_count}개) {post.title}<br></div>')
    print('<br>')

    print(f'<b><span style="font-size: 14pt;">=== {GALL_NAME}에서 조회수가 제일 적은 게시글 ===</span></b><br>')
    for k, post in enumerate(view_bot):
        print(
            f'<div><a href="/mgallery/board/view/?id={GALL_ID}&no={post.pk}">{k + 1}위</a> (조회수 {"%3d" % post.view_count}개) {post.title}<br></div>')
    print('<br>')

    word_used_count = collections.defaultdict(int)
    processed_title = []
    for title in titles:
        process_result = process_title(title, folder)
        for word in process_result['recognized_title']:
            word_used_count[word] += 1
        processed_title.append(process_result)
    word_used_count = {k: v for k, v in sorted(word_used_count.items(), key=lambda item: item[1], reverse=True)}

    print(
        f'<b><span style="font-size: 14pt;">=== {GALL_NAME}에서 빈번하게 사용하는 인물/개념들 ===</span></b>')
    for k, word in enumerate(word_used_count):
        print('<p>' + word + '　' * (6 - len(word)), '%d회' % word_used_count[word] + '</p>')
        if k > 20:
            break
    print('</span>')
    if show_unrecognized_data:
        print('해석하지 못 한 데이터들')
        random.shuffle(processed_title)
        k = 0
        for unrecognized_title in enumerate(processed_title):
            if unrecognized_title['unrecognized_title'] == '':
                continue
            if k > 5:
                break
            print('< %s > %s' % (unrecognized_title['unrecognized_title'], unrecognized_title['org_title']))
            k += 1


if __name__ == '__main__':
    standard_get_data()
    recognize_data()
