import pandas as pd
import geopandas as gpd
from tqdm import tqdm
import re

class DataPreparation:
    def year_finder(df):
        for i in tqdm(range(len(df))):
            if df.loc[i, 'дата создания'] == None or len(str(df.loc[i, 'дата создания'])) == 0:
                df.loc[i, 'building_year'] = 0
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
            df.loc[i, 'building_year'] = int(year)
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
        for i in range(len(gdf)):
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
    # Функция для подсчета совпадений
    def count_matches(protection, keywords):
        return sum(1 for keyword in keywords if re.search(keyword, protection))

    def protection(gdf):
        for j in range(len(gdf)):
            text = str(gdf.loc[j, 'описание предмета охраны'])
            tokens = word_tokenize(text)
            tokens_without_punct = [i for i in tokens if i not in punctuations]
            low_tokens = [i.lower() for i in tokens_without_punct]
            lemms = [morph.parse(i)[0].normal_form for i in low_tokens]
            gdf.loc[j, 'protection'] =  ' '.join(str(el) for el in lemms)

        keywords = [
            'градостроительный значение',
            'объёмно-пространственный',
            'композиция и архитектурно-художественный оформление фасад',
            'планировочный структура и элемент архитектурный оформление интерьер здание'
        ]
            
        # Применяем функцию ко всем элементам DataFrame
        gdf['count'] = gdf['protection'].apply(lambda x: DataMethodPreparation.count_matches(str(x), keywords))
        return(gdf)
    
    def functional_landuse(gdf):
        for i in range(len(gdf)):
            if gdf.loc[i, 'usage'] in ['эксплуатация и обслуживание здания заочной школы',
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
                                                'для эксплуатации и обслуживания здания детской музыкальной школы', 'музей']:
                gdf.loc[i, 'land_use'] = 'buildings'

            elif gdf.loc[i, 'usage'] in ['эксплуатация и обслуживание здания санитарно-эпидемиологической станции', 'для ведения личного подсобного хозяйства', 'Для ведения религиозно-обрядовой деятельности']:
                gdf.loc[i, 'land_use'] = 'other'
        return(gdf)

    def functional_building(gdf):
        for i in range(len(gdf)):
            if gdf.loc[i, 'Функциональная группа'] in ['Дома малоэтажной жилой застройки, в том числе индивидуальной жилой застройки - индивидуальные, малоэтажные блокированные (таунхаусы)', 'Многоквартирные дома (дома средне- и многоэтажной жилой застройки)']:
                gdf.loc[i, 'function'] = 'living'
            elif gdf.loc[i, 'Функциональная группа'] == 'Учебные, спортивные объекты, объекты культуры и искусства, культовые объекты, музеи, лечебно-оздоровительные и общественного назначения объекты':
                gdf.loc[i, 'function'] = 'commercial'
            elif gdf.loc[i, 'Функциональная группа'] in ['Сооружения', 'Административные и бытовые объекты']:
                gdf.loc[i, 'function'] = "industrial"
        return(gdf)

    def material(gdf):
        for i in range(len(gdf)):
            if gdf.loc[i, 'Материал наружных стен'] == 'Рубленые':
                gdf.loc[i, 'material'] = 'wood'
            elif gdf.loc[i, 'Материал наружных стен'] == 'Кирпичные':
                gdf.loc[i, 'material'] = 'stone'
            else:
                gdf.loc[i, 'material'] = 'unknown'
        return(gdf)


    def start_all(gdf):
        DataMethodPreparation.protection(gdf)
        DataMethodPreparation.functional_landuse(gdf)
        DataMethodPreparation.functional_building(gdf)
        DataMethodPreparation.material(gdf)