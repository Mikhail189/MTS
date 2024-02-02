import scrapy
import re
from scrapy.exporters import CsvItemExporter


class FilmItem(scrapy.Item):
    name = scrapy.Field()
    genre = scrapy.Field()
    director = scrapy.Field()
    country = scrapy.Field()
    year = scrapy.Field()
    IMDB = scrapy.Field()

class WikiSpider(scrapy.Spider):
    name = "wiki"
    allowed_domains = ["ru.wikipedia.org", "www.imdb.com"]
    start_urls = ['https://ru.wikipedia.org/wiki/Категория:Фильмы_по_алфавиту']

    custom_settings = {
        'FEED_FORMAT': 'csv',
        'FEED_URI': 'films.csv',
        'ENCODING': 'utf-8'
    }

    def parse(self, response):
        # Извлекаем ссылки на страницы фильмов и следуем по ним
        films = response.css('div.mw-category-group ul li a::attr(href)').getall()
        for film in films:
            yield response.follow(film, callback=self.parse_film)

        next_page = response.css('a:contains("Следующая страница")::attr(href)').get()
        next_page = 'https://ru.wikipedia.org/' + next_page
        if next_page:
            yield response.follow(next_page, self.parse)

    def parse_film(self, response):
        # Создаем экземпляр элемента для хранения собранной информации
        film_item = FilmItem()
        # Ищем информацию в карточке фильма
        table_rows = response.xpath('//table[contains(@class, "infobox")]/tbody/tr')
        for s, row in enumerate(table_rows):
            head = row.xpath('.//th/text()').get(default='')
            head_links = row.xpath('.//th//a/text()').getall()
            if ' Жанры\n' in head_links or ' Жанр \n' in head_links:
                genre = ' '.join(row.xpath('.//td//text()').getall()).strip()
                film_item['genre'] = clean(genre)
            if s == 0:
                film_item['name'] = head
            elif head == 'Режиссёр' or head == 'Режиссёры':
                director_xpath = f'.//th[contains(text(), "{head}")]/following-sibling::td//text()'
                director_list = row.xpath(director_xpath).getall()
                director = ' '.join(director_list).strip()
                film_item['director'] = clean(director)
            elif head == 'Страна' or head == 'Страны':
                country_xpath = f'.//th[contains(text(), "{head}")]/following-sibling::td//text()'
                country_list = row.xpath(country_xpath).getall()
                country = ' '.join(country_list).strip()
                film_item['country'] = clean(country)
            elif head == 'Год' or head == 'Первый показ':
                film_item['year'] = clean(' '.join(row.xpath('.//td//text()').getall()).strip())
        film_item["IMDB"] = None

        imdb_url = response.xpath('//*[@data-wikidata-property-id="P345"]//a/@href').extract_first()
        if imdb_url:
            yield scrapy.Request(imdb_url, callback=parse_imdb_rating, cb_kwargs={'film_item': film_item})
        else:
            yield film_item

def parse_imdb_rating(response, film_item):
    film_item['IMDB'] = response.xpath(
        '//div[@data-testid="hero-rating-bar__aggregate-rating__score"]//text()').extract_first()
    yield film_item


def clean(text):
    text = re.sub(r'\[\w*\]', '', text)
    text = re.sub(r'\xa0', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\s+,', ',', text)
    return text.strip()