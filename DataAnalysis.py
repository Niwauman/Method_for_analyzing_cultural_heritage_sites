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
        