import asyncio
import collections
import io
import statistics
import bs4
import requests_async as req

GALL_NAME = "새보수갤"
GALL_ID = 'newconservativeparty'
URL = f'https://m.dcinside.com/board/{GALL_ID}'
header = {'Host': 'gall.dcinside.com', 'Pragma': 'no-cache',
          'User-Agent': 'Mozilla/5.0 (Linux; Android 7.0; SM-G892A Build/NRD90M; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/67.0.3396.87 Mobile Safari/537.36'}


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
        self.dislike_count = 0
        self.comment_count = 0
        self.time = ''

    def __str__(self):
        json = {}
        for k in [k for k in dir(self) if not callable(getattr(self, k)) and not k.startswith("__")]:
            json[k] = getattr(self, k)
        return str(json)

    def __repr__(self):
        return self.__str__()

    @staticmethod
    def from_post(json: dict):
        post = Post()
        for k in [k for k in dir(post) if not callable(getattr(post, k)) and not k.startswith("__")]:
            setattr(post, k, json[k])
        return post


async def crawling(page: int):
    print(f'page {page} crawling starts')
    data = {}
    for _ in range(10):
        try:
            res = await req.get(f'{URL}?page={page}', headers=header, cookies={'list_count': '200'})
            if res.status_code != 200:
                raise UnexpectedStatus
            break
        except:
            pass
    # print(content)
    for post_node in bs4.BeautifulSoup(res.content.decode('utf-8'), features='html.parser').find_all('div', attrs={
        'class': 'gall-detail-lnktb'}):
        try:
            post_obj = Post()
            text = post_node.findChild().attrs['href']
            text = text[len('https://gall.dcinside.com/board/newconservativeparty/'):]
            post_obj.pk = int(text[:text.rfind('?')])
            print(f'post {post_obj.pk} crawling starts')

            post_obj.title = post_node.find('span', attrs={'class': 'detail-txt'}).text

            if post_node.find('span', attrs={'class': 'sp-lst-img'}):
                post_obj.is_pic = True
            if post_node.find('span', attrs={'class': 'sp-lst-recoimg'}):
                post_obj.is_pic = True
                post_obj.is_rcm = True
            if post_node.find('span', attrs={'class': 'sp-lst-recotxt'}):
                post_obj.is_rcm = True

            for _ in range(10):
                try:
                    res_post = await req.get(f'{URL}/{post_obj.pk}', headers=header)
                    if res_post.status_code != 200:
                        raise UnexpectedStatus
                    break
                except:
                    pass
            detail_node = bs4.BeautifulSoup(res_post.content.decode('utf-8'), features='html.parser')

            post_obj.time = detail_node.find('div', attrs={'class': 'btm'}).findChild().findChildren()[-1].text

            view_count, unused, comment_count = detail_node.find('div', attrs={
                'class': 'gall-thum-btm-inner'}).findChild().findChildren()[0:3]

            post_obj.view_count = int(view_count.text[4:])
            post_obj.comment_count = int(comment_count.text[3:])

            post_obj.like_count = int(detail_node.find('span', attrs={'id': 'recomm_btn'}).text)
            post_obj.dislike_count = int(detail_node.find('span', attrs={'id': 'nonrecomm_btn'}).text)
            data[post_obj.pk] = post_obj
            print(f'post {post_obj.pk} crawling ends')
        except AttributeError as e:
            print(f'post {post_obj.pk} crawling interupts')
    print(f'page {page} crawling ends')
    return data


def process_title(title: str, folder: dict, unnecessary_words: list):
    org_title = title
    title_length = len(title)

    unrecognized_title = ''
    recognized_title = []
    add_delimiter_before = False
    while title_length > 0:
        for word in unnecessary_words:
            length = len(word)
            if word == title[:length]:
                title = title[length:]
                title_length = len(title)
                add_delimiter_before = True
        for length in folder:
            if length < title_length:
                for word in folder[length]:
                    if word == title[:length]:
                        recognized_title.append(folder[length][word])
                        title = title[length:]
                        title_length = len(title)
                        add_delimiter_before = True
        if title_length > 0:
            ch = title[0]
            if not (ch == '\f' or ch == '\n' or ch == '\v' or ch == '\t' or ch == '\r'):
                if add_delimiter_before and len(unrecognized_title) > 0:
                    unrecognized_title += '|'
                    add_delimiter_before = False
                unrecognized_title += ch
            title = title[1:]
            title_length -= 1

    return {'recognized_title': recognized_title, 'unrecognized_title': unrecognized_title, 'org_title': org_title}


def list_idea(posts: list, folder, unnecessary_words: list):
    word_used_count = collections.defaultdict(int)
    processed_title = []
    for post in posts:
        process_result = process_title(post.title, folder, unnecessary_words)
        for word in process_result['recognized_title']:
            word_used_count[word] += 1
        processed_title.append(process_result)

    word_used_count = {k: v for k, v in sorted(word_used_count.items(), key=lambda item: item[1], reverse=True)}

    for k, word in enumerate(word_used_count):
        if k > 100:
            break
        print(f'{word}         {word_used_count[word]}회')

    return processed_title


def get_micro_words(word: str):
    micro_words = []
    for x in range(2, len(word) + 1):
        for y in range(len(word) - x):
            micro_word = word[y:y + x]
            if micro_word.find(' ') == -1 and micro_word.find('|') == -1:
                micro_words.append(micro_word)
    return micro_words


def get_words(content: str):
    dictionary = {}
    for line in content.split('\n'):
        if len(line) == 0:
            continue
        if line[0] == '#':
            continue
        for idea in line.split(','):
            words = idea.split('|')
            for word in words:
                if len(word) > 0:
                    word = word.replace('&comma;', ',')
                    if word not in dictionary:
                        dictionary[word] = words[0]
                    else:
                        print(f'중북된 단어, {word}가 존재합니다!')
    return dictionary


def get_folder(files: list):
    folder = {}
    for filename in files:
        with io.open(f'dict/{filename}.txt', 'r', encoding='utf-8') as file:
            dictionary = get_words(file.read())
            for word in dictionary:
                if len(word) not in folder:
                    folder[len(word)] = {}
                if word not in folder[len(word)]:
                    folder[len(word)][word] = dictionary[word]

    return folder


def process_word(word: str):
    print(word)
    s = input(word)
    if len(s) > 0:
        with open(s, 'a') as file:
            file.write(',' + word)


def get_potential_word(processed_title=None, posts=None, folder=None, unnecessary_words=None, unnecessary_suffixes=None):
    unknown_word_folder = {}
    if processed_title:
        for unrecognized_title in processed_title:
            if len(unrecognized_title['unrecognized_title']) >= 2:
                for micro_word in get_micro_words(unrecognized_title['unrecognized_title']):
                    if not (len(micro_word) in unknown_word_folder):
                        unknown_word_folder[len(micro_word)] = collections.defaultdict(int)
                    unknown_word_folder[len(micro_word)][micro_word] += 1
    if posts:
        for post in posts:
            title = post.title
            for unnecessary_word in unnecessary_words:
                title = title.replace(unnecessary_word, ' ')
                title = title.replace('  ', ' ')
            if len(title) in folder:
                if title in folder[len(title)]:
                    continue
            for micro_word in get_micro_words(title):
                for unnecessary_suffix in unnecessary_suffixes:
                    if micro_word.endswith(unnecessary_suffix):
                        micro_word = micro_word[:-len(unnecessary_suffix)]
                if len(micro_word) in folder:
                    if micro_word in folder[len(micro_word)]:
                        continue
                if not (len(micro_word) in unknown_word_folder):
                    unknown_word_folder[len(micro_word)] = collections.defaultdict(int)
                unknown_word_folder[len(micro_word)][micro_word] += 1


    unknown_word_folder = [v for k, v in
                           sorted(unknown_word_folder.items(), key=lambda item: item[0], reverse=True) if k > 2]
    count = 0
    for unknown_words in unknown_word_folder:
        unknown_words = {k: v for k, v in sorted(unknown_words.items(), key=lambda item: item[1], reverse=True) if
                         v > 3}
        for unknown_word in unknown_words:
            print(unknown_word)
            count += 1
            # if count > 20:
            #    break
        if count > 20:
            break


def recognize_data():
    posts = []
    with io.open('data', 'r', encoding='utf-8') as file:
        for post in eval(file.read()):
            posts.append(Post.from_post(post))

    folder = get_folder(['common', 'countries', 'estate', 'men', 'politics', 'others'])

    with io.open('dict/unnecesary.txt', 'r', encoding='utf-8') as file:
        unnecessary_words = get_words(file.read())

    with io.open('dict/unnecesary_suffix.txt', 'r', encoding='utf-8') as file:
        unnecessary_suffixes = get_words(file.read())

    post_sort_by_recommend = sorted(posts,
                                    key=lambda post: (post.like_count - post.dislike_count) / (post.view_count + 1) - 0.5,
                                    reverse=True)

    word_point = collections.defaultdict(list)
    word_count = collections.defaultdict(int)
    for post in posts:
        point = (post.like_count - post.dislike_count) * post.view_count
        process_result = process_title(post.title, folder, unnecessary_words)
        for word in process_result['recognized_title']:
            word_point[word].append(point)
            word_count[word] += 1

    word_used_count = {k: v for k, v in sorted(word_point.items(), key=lambda item: statistics.median(item[1]), reverse=True)}
    k = 0
    for word in word_used_count:
        if k > 20:
            break
        k += 1
        print(word)




    
    post_sort_by_issued = sorted(posts, key=lambda post: (post.like_count + post.dislike_count + post.comment_count) / (
            post.view_count + 1), reverse=True)

    
    print('개추받는 게시물 TOP 10')
    for post in post_sort_by_recommend[:10]:
        print(post.pk, post.title, post.time)
    print()

    print('비추받는 게시물 TOP 10')
    for post in reversed(post_sort_by_recommend[-10:]):
        print(post.pk, post.title, post.time)
    print()

    print('주목되는 게시물 TOP 10')
    for post in post_sort_by_issued[:10]:
        print(post.pk, post.title, post.time)
    print()

    # list_top_comments(posts)
    # list_top_likes(posts)
    # list_top_views(posts)
    # list_bot_views(posts)

    # processed_title = list_idea(posts, folder, unnecessary_words)

    # get_potential_word(posts=posts, folder=folder, unnecessary_words=unnecessary_words, unnecessary_suffixes=unnecessary_suffixes)


MAX_POST = 50
MAX_CONNECTION = 5


def get_post_data_standard():
    total_posts = {}
    loop = asyncio.get_event_loop()
    for j in range(MAX_POST // MAX_CONNECTION):
        tasks = []
        for k in range(MAX_CONNECTION):
            tasks.append(loop.create_task(crawling(j * MAX_CONNECTION + k + 2)))
        loop.run_until_complete(asyncio.wait(tasks))
        for task in tasks:
            posts = task.result()
            for post in posts:
                total_posts[post] = posts[post]
    loop.close()
    with io.open('data', 'w', encoding='utf-8') as file:
        file.write(str(list(total_posts.values())))


if __name__ == '__main__':
    # get_post_data_standard()
    recognize_data()
