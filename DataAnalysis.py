import pandas as pd
import geopandas as gpd
from tqdm import tqdm
import re
import osmnx as ox

class DataPreparation:
    def year_finder(df):
        for i in tqdm(range(len(df))):
            if df.loc[i, 'дата создания'] == None or len(str(df.loc[i, 'дата создания'])) == 0:
                df.loc[i, 'DATE_BUILD'] = 1900
            else:
                year = str(df.loc[i, 'дата создания'])
                year_ = re.search('(\d{4})', str(df.loc[i, 'дата создания']))
                if year_ != None:
                    year = int(year_.group())
                elif re.search('XVIII', year) != None:
                    year = 1750 
                elif re.search('XVII', year) != None:
                    year = 1650
                elif re.search('XVI', year) != None:
                    year = 1550
                elif re.search('XV', year) != None:
                    year = 1450
                elif re.search('XIX', year) != None:
                    year = 1850
                elif re.search('XX', year) != None:
                    year = 1910
                elif re.search('XIV', year) != None:
                    year = 1350
                elif re.search('19', year) != None:
                    year = 1910
                else:
                    year = 0
            df.loc[i, 'DATE_BUILD'] = int(year)
        return df
    
    def separator_reestr(df, region):
        heritage_df = df[df['Регион'] == region].reset_index ()
        heritage_df = DataPreparation.year_finder(heritage_df)
        print(heritage_df['Регион'].head(3))
        # Разделение исходного ДФ на части с исходными координатами и без
        heritage_coor = heritage_df.dropna(subset=['На карте']).reset_index()
        heritage_none = heritage_df[heritage_df['На карте'].isna()].reset_index()
        print(f'Всего объектов: {len(heritage_df)}')
        print(f'Количество объектов с координатами: {len(heritage_coor)}')
        print(f'Количество объектов без координат: {len(heritage_none)}')
        for j in range(len(heritage_coor)):
            heritage_coor.loc[j, 'lat'] = (str(heritage_coor.loc[j, 'На карте'])).split('[')[1].split(']')[0].split(',')[1]
            heritage_coor.loc[j, 'lon'] = (str(heritage_coor.loc[j, 'На карте'])).split('[')[1].split(']')[0].split(',')[0]
        heritage_coor = gpd.GeoDataFrame(heritage_coor, geometry=gpd.points_from_xy(heritage_coor.lon, heritage_coor.lat), crs = 'EPSG:4326')
        heritage_df = pd.concat([heritage_coor, heritage_none], ignore_index=True)
        heritage_gdf = gpd.GeoDataFrame(heritage_df, geometry='geometry', crs = 'EPSG:4326')
        return heritage_gdf, heritage_coor, heritage_none

    def number_report(gdf):
        for i in gdf.index:
            desc = gdf.loc[i, 'Культурное наследие (описание)']
            # Выделяем реестровые номера в отдельный столбец
            if re.search('рег.номер', desc) != None:
                if re.search('35-', desc):
                    desc = desc.split('рег.номер')[1].replace(' ', '').replace(')', '')
                    gdf.loc[i, 'учетный номер'] = desc
                    gdf.loc[i, 'Номер в реестре'] = 0
                else:
                    desc = desc.split('рег.номер')[1].replace(' ', '').replace(')', '')
                    gdf.loc[i, 'Номер в реестре'] = desc
                    gdf.loc[i, 'учетный номер'] = 0
            # Объединяем столбцы с годом заверешния строительства и года ввода в эусплуатацию
            if len(str(gdf.loc[i, 'Год завершения строительства'])) < 2:
                gdf.loc[i, 'Год завершения строительства'] = gdf.loc[i, 'Год ввода в эксплуатацию']
        return gdf
    
    def merge_reestr_building(gdf, building_osm):
        for i in building_osm.index:
            poly = building_osm.loc[i,'geometry'].buffer(15)
            for j in gdf.index:
                point = gdf.loc[j,'geometry']
                if poly.contains(point):
                    building_osm.loc[i,'_building_year'] = gdf.loc[j,'DATE_BUILD']
                    building_osm.loc[i,'_arch_style'] = gdf.loc[j,'ARCH_STYLE']
                    building_osm.loc[i,'_material'] = gdf.loc[j,'MATERIAL']
                    building_osm.loc[i,'_building_floor'] = gdf.loc[j,'FLOOR']
                    building_osm.loc[i,'_culture_heritage'] = 1
        return(building_osm)
                    



from nltk.tokenize import word_tokenize
import nltk
from string import punctuation
import pymorphy3
#записываем в morph лемматизатор
punctuations = list(punctuation)
nltk.download('stopwords')
nltk.download('punkt_tab')
stopwords = nltk.corpus.stopwords.words('russian')
morph = pymorphy3.MorphAnalyzer()

class DataMethodPreparation:

    def land_cad_cost(gdf):
        gdf['ZY_AREA'] = gdf['ZY_AREA'].fillna(1)
        gdf['ZY_KADCOST'] = round(gdf['ZY_KADCOST'] / gdf['ZY_AREA'], 2)
        gdf['ZY_KADCOST'] = gdf['ZY_KADCOST'].fillna(1)



    def floor_count(gdf):
        for i in gdf.index:
            gdf['Количество подземных этажей'] = gdf['Количество подземных этажей'].fillna(0)
            if len(gdf.loc[i,'Количество этажей (в том числе подземных)']) > 2:
                gdf.loc[i,'FLOOR'] = int(gdf.loc[i,'Количество этажей (в том числе подземных)'].split('-')[0].split('+')[0]) - int(str(gdf.loc[i,'Количество подземных этажей']).replace('подвал', '1').replace('нет', '0'))
                if gdf.loc[i,'FLOOR'] == 0:
                    gdf.loc[i,'FLOOR'] = 1
            else: gdf.loc[i,'FLOOR'] = gdf.loc[i,'Количество этажей (в том числе подземных)']
        return(gdf)


    # Функция для подсчета совпадений
    def count_matches(protection, keywords):
        return sum(1 for keyword in keywords if re.search(keyword, protection))

    def protection(gdf):
        for j in gdf.index:
            text = str(gdf.loc[j, 'PROTECTION'])
            tokens = word_tokenize(text)
            tokens_without_punct = [i for i in tokens if i not in punctuations]
            low_tokens = [i.lower() for i in tokens_without_punct]
            lemms = [morph.parse(i)[0].normal_form for i in low_tokens]
            gdf.loc[j, 'PROTECTION'] =  ' '.join(str(el) for el in lemms)

        keywords = [
            'градостроительный значение',
            'объёмно-пространственный',
            'композиция и архитектурно-художественный оформление фасад',
            'планировочный структура и элемент архитектурный оформление интерьер здание'
            'месторасположение и градостроительный характеристика'
        ]
            
        # Применяем функцию ко всем элементам DataFrame
        gdf['PROTECTION_SUM'] = gdf['PROTECTION'].apply(lambda x: DataMethodPreparation.count_matches(str(x), keywords))
        return(gdf)
    
    def functional_landuse(gdf):
        for i in range(len(gdf)):
            if gdf.loc[i, 'ZY_VRI'] in ['эксплуатация и обслуживание здания заочной школы',
                                                'объекты культуры и искусства районного и местного значения',
                                                'для эксплуатации и обслуживания памятника архитектуры (дом Засецких) и здания гаража',
                                                'Индивидуальные жилые дома',
                                                'индивидуальные жилые дома',
                                                'нежилое здание',
                                                'эксплуатация и обслуживание административного здания',
                                                'для эксплуатации и обслуживания многоквартирного дома',
                                                'для эксплуатации и обслуживания жилого дома',
                                                'эксплуатация и обслуживание нежилых помещений здания',
                                                'эксплуатация административного здания',
                                                'для эксплуатации и обслуживания здания детской музыкальной школы', 'музей','Малоэтажная многоквартирная жилая застройка']:
                gdf.loc[i, 'ZY_VRI'] = 'buildings'

            elif gdf.loc[i, 'ZY_VRI'] in ['эксплуатация и обслуживание здания санитарно-эпидемиологической станции', 'для ведения личного подсобного хозяйства', 'Для ведения религиозно-обрядовой деятельности']:
                gdf.loc[i, 'ZY_VRI'] = 'other'
        return(gdf)

    def functional_building(gdf):
        for i in range(len(gdf)):
            if gdf.loc[i, 'Функциональная группа'] in ['Дома малоэтажной жилой застройки, в том числе индивидуальной жилой застройки - индивидуальные, малоэтажные блокированные (таунхаусы)', 
                                                       'Многоквартирные дома (дома средне- и многоэтажной жилой застройки)',
                                                       'Объекты временного проживания, включая объекты рекреационно-оздоровительного значения']:
                gdf.loc[i, 'BLD_USAGE'] = 'living'
            elif gdf.loc[i, 'Функциональная группа'] in ['Учебные, спортивные объекты, объекты культуры и искусства, культовые объекты, музеи, лечебно-оздоровительные и общественного назначения объекты', 
                                                         'Объекты коммерческого назначения, предназначенные для оказания услуг населению, включая многофункционального назначения']:
                gdf.loc[i, 'BLD_USAGE'] = 'commercial'
            elif gdf.loc[i, 'Функциональная группа'] in ['Сооружения', 'Административные и бытовые объекты',
                                                         'Объекты, предназначенные для хранения транспорта',
                                                         'Объекты производственного назначения, за исключением передаточных устройств и сооружений',
                                                         'Прочие объекты', 'Сооружения']:
                gdf.loc[i, 'BLD_USAGE'] = "industrial"
        return(gdf)

    def material(gdf):
        for i in gdf.index:
            if gdf.loc[i, 'MATERIAL'] in ['Рубленые', 'Деревянные',  ]:
                gdf.loc[i, 'MATERIAL'] = 'wood'
            elif  gdf.loc[i, 'MATERIAL'] in ['Каменные и деревянные', 'Кирпичные; Рубленые', 'Кирпичные; Дощатые', 'Каменные; Деревянные', 'Рубленые; Кирпичные']:
                gdf.loc[i, 'MATERIAL'] = 'wood, stone'
            elif gdf.loc[i, 'MATERIAL'] in ['Кирпичные', 'Из железобетонных сегментов', 'Каменные']:
                gdf.loc[i, 'MATERIAL'] = 'stone'
            elif  gdf.loc[i, 'MATERIAL'] in ['Из прочих материалов', 'Смешанные']:
                gdf.loc[i, 'MATERIAL'] = 'unknown'
            else:
                gdf.loc[i, 'MATERIAL'] = 'unknown'
        return(gdf)


    def start_all(gdf):
        DataMethodPreparation.land_cad_cost(gdf)
        DataMethodPreparation.floor_count(gdf)
        DataMethodPreparation.protection(gdf)
        DataMethodPreparation.functional_landuse(gdf)
        DataMethodPreparation.functional_building(gdf)
        DataMethodPreparation.material(gdf)
        return(gdf)
    
class DataDonwload:
    def parcer_osm(region, tag_str, tag_def = True): #На первом месте указываем тег, на втором его значение по умолчанию выбираются все значения
        tags = {tag_str: tag_def}
        objects = ox.features.features_from_polygon(region.union_all(), tags)
        return objects

    def data_osm(city):
        region = ox.geocode_to_gdf(query=city).reset_index()
        try:
            building_osm = DataDonwload.parcer_osm(region,'building').reset_index()
        except:
            print('Не найдены здания. Проверьте правильность написания названия территории или внесите данные вручную')
            building_osm = pd.DataFrame(columns=['NUM', 'NAME'])
        try:
            shop = DataDonwload.parcer_osm(region,'shop').reset_index()
        except:
            print('Не найдены объекты тороговли. Проверьте правильность написания названия территории или внесите данные вручную')
            shop = pd.DataFrame(columns=['NUM', 'NAME'])
        try:
            cafe = DataDonwload.parcer_osm(region,'amenity', ['bar', 'cafe', 'fast_food', 'food_court', 'pub', 'restaurant']).reset_index()
        except:
            print('Не найдены объекты питания. Проверьте правильность написания названия территории или внесите данные вручную')
            cafe = pd.DataFrame(columns=['NUM', 'NAME'])
        try:
            public_transport = DataDonwload.parcer_osm(region,'public_transport').reset_index()
        except:
            print('Не найдены остановки общественного транспорта. Проверьте правильность написания названия территории или внесите данные вручную')
            public_transport = pd.DataFrame(columns=['NUM', 'NAME'])
        return(region, building_osm, shop, cafe, public_transport)