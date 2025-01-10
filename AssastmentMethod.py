import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, Polygon, MultiPoint

from objectnat import get_boundary
from objectnat import get_accessibility_isochrones
from objectnat import get_walk_graph
from objectnat import get_visibility

from DataAnalysis import DataPreparation as DataPreparation

import json
# Закружаем критерии оценки
with open("Example_files/criteria.json", encoding="UTF-8") as file_in:
    criteria = json.load(file_in)

# Закружаем критерии риски
with open("Example_files/risks.json", encoding="UTF-8") as file_in:
    risks = json.load(file_in)

class AspectLaw:
    #subject_of_protection
    def subject_of_protection(gdf):
        for i in range(len(gdf)):
            count_build = gdf.loc[i, 'count']
            for count_table in criteria[0]['law_aspect']['subject_of_protection']:
                if int(count_table) == int(count_build):
                    gdf.loc[i, 'score_protection'] = criteria[0]['law_aspect']['subject_of_protection'][count_table]
        return(gdf)

    # permitted_land_use
    def permitted_land_use(gdf):
        for i in range(len(gdf)):
            land_use_build = gdf.loc[i, 'land_use']
            for land_use_table in criteria[0]['law_aspect']['permitted_land_use']:
                if land_use_table == land_use_build:
                    gdf.loc[i, 'score_land_use'] = criteria[0]['law_aspect']['permitted_land_use'][land_use_table]
            gdf['score_land_use'] = gdf['score_land_use'].fillna(0)
        return(gdf)

    # cadastral_integrity
    def cadastral_integrity (gdf):
        for i in range(len(gdf)):
            cadastral_number = str(gdf.loc[i, 'Кадастровые номера ЗУ, в пределах которых расположен данный ОН']).split(';')
            if len(cadastral_number) == 1:
                gdf.loc[i, 'score_cadastral_integrity'] = 1
            else:
                gdf.loc[i, 'score_cadastral_integrity'] = 0
        return(gdf)
    
    def start_all(gdf):
        gdf=AspectLaw.subject_of_protection(gdf)
        gdf=AspectLaw.permitted_land_use(gdf)
        gdf=AspectLaw.cadastral_integrity(gdf)

        # Итоговый бал по аспекту
        gdf['total_law_score'] = 1.25 * gdf['score_cadastral_integrity'] + 1.33 * gdf['score_land_use'] + 1.42 * gdf['score_protection']
        gdf['total_law_percent'] = round(gdf['total_law_score'] / 3 * 100, 2)
        return(gdf)

class AspectPhysical:

    # material
    def material(gdf):
        for i in range(len(gdf)):
            material_build = gdf.loc[i, 'material']
            for material_table in criteria[0]['physical_aspect']['material']['name']:
                if material_table == material_build:
                    gdf.loc[i, 'score_material'] = criteria[0]['physical_aspect']['material']['name'][material_table]
        return(gdf)

    # function
    def function(gdf):
        for i in range(len(gdf)):
            function_build = gdf.loc[i, 'function']
            for function_table in criteria[0]['physical_aspect']['function']:
                if function_table == function_build:
                    gdf.loc[i, 'score_function'] = criteria[0]['physical_aspect']['function'][function_table]
        return(gdf)

    # percentage_of_construction
    def percentage_of_construction(gdf):
        gdf['area'] = gdf['area'].fillna(0)
        for i in range(len(gdf)):
            if gdf.loc[i, 'area'] == 0:
                percent_build = 100
            else:
                if len(gdf.loc[i, 'Количество этажей (в том числе подземных)']) > 2:
                    gdf.loc[i, 'Количество этажей (в том числе подземных)'] = gdf.loc[i, 'Количество этажей (в том числе подземных)'].split('-')[0]
                percent_build = (gdf.loc[i, 'Площадь, кв.м'] / int(gdf.loc[i, 'Количество этажей (в том числе подземных)'])) / gdf.loc[i, 'area'] * 100
            gdf.loc[i, 'percentage_of_construction'] = percent_build
            percent_table_prev = 0.0
            for percent_table in criteria[0]['physical_aspect']['percentage_of_construction']:
                if float(percent_build) > percent_table_prev and float(percent_build) <= float(percent_table):
                    gdf.loc[i, 'score_percentage_of_construction'] = criteria[0]['physical_aspect']['percentage_of_construction'][percent_table]      
                percent_table_prev = float(percent_table)
        return(gdf)
    
    def accident(gdf):
        for i in range(len(gdf)):
            if gdf.loc[i,'Объект признан аварийным '] == 'да':
                gdf.loc[i,'score_accident'] = 0
            else:
                gdf.loc[i,'score_accident'] = 1
        return(gdf)
    
    def recover_engineering_communications(gdf):
        for i in range(len(gdf)):
            if gdf.loc[i,'Объект признан аварийным '] == 'да':
                gdf.loc[i,'water_cold'] = 0
                gdf.loc[i,'water_hot'] = 0
                gdf.loc[i,'water_out'] = 0
                gdf.loc[i,'electricity'] = 1
                gdf.loc[i,'fire_system'] = 0

            if gdf.loc[i,'Совокупный износ'] > 0.8:
                gdf.loc[i,'water_cold'] = 1
                gdf.loc[i,'water_hot'] = 0
                gdf.loc[i,'water_out'] = 1
                gdf.loc[i,'electricity'] = 1
                gdf.loc[i,'fire_system'] = 0
            elif gdf.loc[i,'Совокупный износ'] <= 0.8 and gdf.loc[i,'Совокупный износ'] >= 0.5:
                gdf.loc[i,'water_cold'] = 1
                gdf.loc[i,'water_hot'] = 1
                gdf.loc[i,'water_out'] = 1
                gdf.loc[i,'electricity'] = 1
                gdf.loc[i,'fire_system'] = 0
            else:
                gdf.loc[i,'water_cold'] = 1
                gdf.loc[i,'water_hot'] = 1
                gdf.loc[i,'water_out'] = 1
                gdf.loc[i,'electricity'] = 1
                gdf.loc[i,'fire_system'] = 1
        return(gdf)



    def start_all(gdf):

        # Оценка износа здания
        gdf['score_deterioration'] = 1 - gdf['Совокупный износ']
        gdf = AspectPhysical.material(gdf)
        gdf = AspectPhysical.function(gdf)
        gdf = AspectPhysical.percentage_of_construction(gdf)
        gdf = AspectPhysical.accident(gdf)
        gdf = AspectPhysical.recover_engineering_communications(gdf)
        gdf['score_engineering_communications'] = gdf['water_cold'] * 0.2 + gdf['water_hot']*0.2+gdf['water_out']*0.2+gdf['electricity']*0.2+gdf['fire_system']*0.2

        # Итоговый бал по аспекту
        gdf['total_physical_score'] = 1.19 * gdf['score_deterioration'] + 1.05 * gdf['score_material'] + 1.10 * gdf['score_function'] + 1.29 * gdf['score_percentage_of_construction']  + 1.05 * gdf['score_accident'] + 1.19 * gdf['score_engineering_communications'] + 1.14 # за текущее использование
        gdf['total_physical_percent'] = round(gdf['total_physical_score'] / 7 * 100, 2)
        return(gdf)

class AspectSpatial:

# get isochrones and calculate services
    def services(gdf, shop, cafe, public_transport, G_walk):

        for i in range(len(gdf)):
            points = gpd.GeoDataFrame(geometry=[gdf.loc[i,'geometry']], crs=4326).to_crs(G_walk.graph['crs'])
            try:
                isochrones, stops, routes = get_accessibility_isochrones(
                points=points,
                weight_type="time_min",
                weight_value=10,
                graph_nx=G_walk
                )
                try:
                    gdf.loc[i, 'count_shop'] = len(shop[shop.geometry.within(isochrones.geometry[0])])
                except AttributeError:
                    gdf.loc[i, 'count_shop'] = 0
                try:
                    gdf.loc[i, 'count_cafe'] = len(cafe[cafe.geometry.within(isochrones.geometry[0])])
                except AttributeError:
                    gdf.loc[i, 'count_cafe'] = 0
                try:
                    gdf.loc[i, 'count_public_transport'] = len(public_transport[public_transport.geometry.within(isochrones.geometry[0])])
                except AttributeError:
                    gdf.loc[i, 'count_public_transport'] = 0
            except ValueError:
                gdf.loc[i, 'count_shop'] = 0
                gdf.loc[i, 'count_cafe'] = 0
                gdf.loc[i, 'count_public_transport'] = 0
            return(gdf)

    def merge_hex_services(hex, cafe, shop, public_transport):

        for i in range(len(hex)):
                # Выбор точек внутри полигона
            points_within_polygon = cafe[cafe.geometry.within(hex.geometry[i])]
            # Группировка значений
            grouped_values = points_within_polygon.groupby('osmid')['amenity'].count().reset_index()
            hex.loc[i, 'count_cafe'] = grouped_values['amenity'].count()
            grouped_values['amenity'] = 0

            points_within_polygon = shop[shop.geometry.within(hex.geometry[i])]
            # Группировка значений
            grouped_values = points_within_polygon.groupby('osmid')['amenity'].count().reset_index()
            hex.loc[i, 'shop'] = grouped_values['amenity'].count()
            grouped_values['shop'] = 0

            # Выбор точек внутри полигона
            points_within_polygon = public_transport[public_transport.geometry.within(hex.geometry[i])]
            # Группировка значений
            grouped_values = points_within_polygon.groupby('osmid')['amenity'].count().reset_index()
            hex.loc[i, 'public_transport'] = grouped_values['amenity'].count()
            grouped_values['public_transport'] = 0
        return(hex)
    
    def services_hex(gdf, hex):
        gdf = gdf.to_crs('EPSG:32637')
        hex = hex.to_crs('EPSG:32637')
        for i in range(len(hex)):
            poly = hex.loc[i, 'geometry']
            for j in range(len(gdf)):
                point = gdf.loc[j,'geometry']
                if poly.contains(point):
                    gdf.loc[j, 'count_cafe'] = hex.loc[i, 'count_cafe']
                    gdf.loc[j, 'count_shop'] = hex.loc[i, 'count_shop']
                    gdf.loc[j, 'count_public_transport'] = hex.loc[i, 'count_public_transport']
        return(gdf)

    def vision(gdf_origin, obstacles,building_osm): # создание полигонов видимости
        gdf=gdf_origin.copy()
        gdf = gdf.to_crs('EPSG:32637')
        obstacles = obstacles.to_crs('EPSG:32637')
        building_osm = building_osm.to_crs('EPSG:32637')
        for i in range(len(building_osm)):
            poly = building_osm.loc[i,'geometry'].buffer(5)
            poly_2 = building_osm.loc[i,'geometry']
            for j in range(len(gdf)):
                point = gdf.loc[j,'geometry']
                if poly.contains(point):
                    gdf.loc[j,'geometry'] = poly_2

        for i in range(len(gdf)):
            dict_vision_poly = {}
            if isinstance(gdf.loc[i, 'geometry'], Point) != True:
                points_list = list(gdf.geometry[i].exterior.coords)
                string = ''
                for string_p in points_list:
                    vision_poly = get_visibility(Point([string_p]), obstacles, 300)
                    dict_vision_poly[string_p] = vision_poly
            else:
                vision_poly = get_visibility(gdf.loc[i, 'geometry'], obstacles, 300)
                dict_vision_poly[gdf.loc[i, 'geometry']] = vision_poly 
        
            vision_poly = gpd.GeoDataFrame(geometry=[j for j in dict_vision_poly.values()], crs=32637)
            unioned_polygon = vision_poly.unary_union
            gdf.loc[i, 'geometry'] = unioned_polygon
        return(gdf)
    
    def view_selection(gdf_vision, building_osm, gdf):
        gdf['score_historicity'] = 0
        for i in range(len(gdf_vision)):
            selection_buildings = gpd.overlay(building_osm, gdf_vision[gdf_vision.index == i], how='intersection')
            if selection_buildings['_culture_heritage'].count() >= 1:
                gdf.loc[i, 'score_historicity'] += 0.1
            floor_mean = selection_buildings['_building_floor'].fillna(1).astype(int).mean()
            if float(gdf.loc[i, 'Количество этажей (в том числе подземных)']) > float(floor_mean - 1) and float(gdf.loc[i, 'Количество этажей (в том числе подземных)']) < float(floor_mean + 1):
                gdf.loc[i, 'score_historicity'] += 0.3
            year_mean = selection_buildings['_building_year'].fillna(1917).astype(int).mean()
            if gdf.loc[i, 'building_year'] > (year_mean - 20) and gdf.loc[i, 'building_year'] < (year_mean + 20):
                gdf.loc[i, 'score_historicity'] += 0.3
        return(gdf)
    
    def score_spatial(gdf):
        gdf['score_services'] = 0
        gdf['score_transport'] = 0
        for i in range(len(gdf)):
            if gdf.loc[i, 'count_shop'] >=1:
                gdf['score_services'] += 0.5
            
            if gdf.loc[i, 'count_cafe'] >=1:
                gdf['score_services'] += 0.5
            
            if gdf.loc[i, 'count_public_transport'] >=2:
                gdf['score_transport'] += 1
        return(gdf)

    def start_all(gdf,shop, cafe, public_transport,building):
        # Fetching the territory boundary using the OSM ID for the specific relation.
        # The OSM ID refers to a particular area on OpenStreetMap.
        bounds = get_boundary(osm_id=1327509)  # OSM ID for https://www.openstreetmap.org/relation/1114252
        # Generating a walking graph for the defined boundary.
        #G_walk = get_walk_graph(polygon=bounds)
        gdf = gdf.to_crs('EPSG:32637')
        building = building.to_crs('EPSG:32637')
        building = DataPreparation.merge_reestr_building(gdf, building)
        
        hex = hex.to_crs('EPSG:32637')
        cafe = cafe.to_crs('EPSG:32637')
        shop = shop.to_crs('EPSG:32637')
        public_transport = public_transport.to_crs('EPSG:32637')

        hex = AspectSpatial.merge_hex_services(gdf,cafe,shop,public_transport)
        gdf = AspectSpatial.services_hex(gdf, hex)

        gdf=AspectSpatial.score_spatial(gdf)
        gdf_vision = AspectSpatial.vision(gdf, building, building)
        gdf_vision = gdf_vision.to_crs('EPSG:32637')
        gdf_vision['geometry'] = gdf_vision['geometry'].buffer(35)
        gdf = AspectSpatial.view_selection(gdf_vision,building,gdf)
        # Итоговый бал по аспекту
        gdf['total_spatial_score'] = 1.50 * gdf['score_services'] + 1.40 * gdf['score_transport'] + 1.10 * gdf['score_historicity']
        gdf['total_spatial_percent'] = round(gdf['total_spatial_score'] / 3 * 100, 2)
        return(gdf)
    


class AspectEconomic:
    def cad_cost_estimation_building(gdf):
        for i in range(len(gdf)):
            cad_cost = gdf.loc[i, 'Удельный показатель кадаcтровой стоимости объекта недвижимости, руб./кв.м']
            if cad_cost == 0:
                q = 'q3'
            elif cad_cost <= gdf['Удельный показатель кадаcтровой стоимости объекта недвижимости, руб./кв.м'].quantile(q = 0.25):
                q = 'q1'
            elif cad_cost <= gdf['Удельный показатель кадаcтровой стоимости объекта недвижимости, руб./кв.м'].quantile(q = 0.50):
                q = 'q2'
            elif cad_cost <= gdf['Удельный показатель кадаcтровой стоимости объекта недвижимости, руб./кв.м'].quantile(q = 0.75):
                q = 'q3'
            else:
                q = 'q4'
            gdf.loc[i, 'score_cadstral_value_building'] = criteria[0]['economic_aspect']['cadstral_value_building'][q]
        return(gdf)

    def cad_cost_estimation_land(gdf):
        for i in range(len(gdf)):
            cad_cost = gdf.loc[i, 'cad_cost']
            if cad_cost == 0:
                q = 'q3'
            elif cad_cost <= gdf['cad_cost'].quantile(q = 0.25):
                q = 'q1'
            elif cad_cost <= gdf['cad_cost'].quantile(q = 0.50):
                q = 'q2'
            elif cad_cost <= gdf['cad_cost'].quantile(q = 0.75):
                q = 'q3'
            else:
                q = 'q4'
            gdf.loc[i, 'score_cadstral_value_land'] = criteria[0]['economic_aspect']['cadstral_value_land'][q]
        return(gdf)
    
    def support_program(gdf):
        for i in range(len(gdf)):
            gdf.loc[i, 'score_support_measures'] = 1  #criteria[0]['economic_aspect']['support_measures'][gdf.loc[i,'actual_program']]
        return(gdf)
    
    def start_all(gdf):
        gdf=AspectEconomic.cad_cost_estimation_building(gdf)
        gdf=AspectEconomic.cad_cost_estimation_land(gdf)
        gdf=AspectEconomic.support_program(gdf)

        # Итоговый бал по аспекту
        gdf['total_economic_score'] = 1.22 * gdf['score_cadstral_value_building'] + 1.22 * gdf['score_cadstral_value_land'] + 1.78 * gdf['score_support_measures']
        gdf['total_economic_percent'] = round(gdf['total_economic_score'] / 3 * 100, 2)
        return(gdf)

class General:
    def calculate_scores(gdf):
        gdf['total_physical_score'] = gdf['score_percentage_of_construction'] + gdf['score_material'] + gdf['score_function'] + gdf['score_deterioration'] + gdf['score_accident']
        gdf['total_spatial_score'] = 0
        gdf['total_law_score'] = gdf['score_cadastral_integrity'] + gdf['score_land_use'] + gdf['score_protection']
        gdf['total_economic_score'] = gdf['score_cadstral_value_building'] + gdf['score_cadstral_value_land']
        gdf['total_score'] = gdf['total_physical_score'] + gdf['total_spatial_score'] + gdf['total_law_score'] + gdf['total_economic_score']
        return(gdf)
    def calculate_scores(gdf):
        gdf['total_score'] = gdf['total_physical_score'] + gdf['total_spatial_score'] + gdf['total_law_score'] + gdf['total_economic_score']
        gdf['total_percent'] = round(gdf['total_score'] / 16 * 100, 2)
        return(gdf)
    def risks_assastment(gdf):
        gdf['risks']=''
        for j in range(len(gdf)):
            for aspect in ['physical_aspect','law_aspect', 'economic_aspect']:
                for risk in risks[0][aspect]:
                    if float(gdf.loc[j, risks[0][aspect][risk]['indicator']]) <= float(risks[0][aspect][risk]['value']):
                        gdf.loc[j, 'risks'] += str(risks[0][aspect][risk]['id']) + ';'
            gdf.loc[j, 'risks_num'] = len(gdf.loc[j, 'risks'].split(';')) - 1
        return(gdf)