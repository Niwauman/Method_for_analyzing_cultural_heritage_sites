import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, Polygon, MultiPoint

from iduedu import get_walk_graph
from  iduedu import config
config.change_logger_lvl('DEBUG')

from objectnat import get_accessibility_isochrones
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
            count_build = gdf.loc[i, 'PROTECTION_SUM']
            for count_table in criteria[0]['law_aspect']['subject_of_protection']:
                if int(count_table) == int(count_build):
                    gdf.loc[i, 'SCORE_PROTECTION'] = criteria[0]['law_aspect']['subject_of_protection'][count_table]
        return(gdf)

    # permitted_land_use
    def permitted_land_use(gdf):
        gdf['SCORE_ZY_VRI'] = 0
        for i in gdf.index:
            land_use_build = gdf.loc[i, 'ZY_VRI']
            for land_use_table in criteria[0]['law_aspect']['permitted_land_use']:
                if land_use_table == land_use_build:
                    gdf.loc[i, 'SCORE_ZY_VRI'] = criteria[0]['law_aspect']['permitted_land_use'][land_use_table]
        gdf['SCORE_ZY_VRI'] = gdf['SCORE_ZY_VRI'].fillna(0)
        return(gdf)

    # cadastral_integrity
    def cadastral_integrity (gdf):
        for i in range(len(gdf)):
            cadastral_number = str(gdf.loc[i, 'KADASTRZY']).split(';')
            if len(cadastral_number) == 1:
                gdf.loc[i, 'SCORE_CAD_INTEGRITY'] = 1
            else:
                gdf.loc[i, 'SCORE_CAD_INTEGRITY'] = 0
        return(gdf)
    
    def start_all(gdf):
        gdf=AspectLaw.subject_of_protection(gdf)
        gdf=AspectLaw.permitted_land_use(gdf)
        gdf=AspectLaw.cadastral_integrity(gdf)

        # Итоговый бал по аспекту
        gdf['TOTAL_ASPECT_LAW'] = round(0.19 * gdf['SCORE_CAD_INTEGRITY'] + 0.29 * gdf['SCORE_ZY_VRI'] + 0.52 * gdf['SCORE_PROTECTION'], 2)
        #gdf['total_law_percent'] = round(gdf['total_law_score'] / 4 * 100, 2) delete
        return(gdf)

class AspectPhysical:

    # material
    def material(gdf):
        for i in range(len(gdf)):
            material_build = gdf.loc[i, 'MATERIAL']
            for material_table in criteria[0]['physical_aspect']['material']['name']:
                if material_table == material_build:
                    gdf.loc[i, 'SCORE_MATERIAL'] = criteria[0]['physical_aspect']['material']['name'][material_table]
        return(gdf)

    # function
    def bld_usage(gdf): # previous was function
        for i in gdf.index:
            function_build = gdf.loc[i, 'BLD_USAGE']
            for function_table in criteria[0]['physical_aspect']['function']:
                if function_table == function_build:
                    gdf.loc[i, 'SCORE_BLD_USAGE'] = criteria[0]['physical_aspect']['function'][function_table]
        return(gdf)

    # percentage_of_construction
    def percentage_of_construction(gdf):
        for i in range(len(gdf)):
            if gdf.loc[i, 'ZY_AREA'] < 3:
                percent_build = 100
            else:
                percent_build = (gdf.loc[i, 'BLD_AREA'] / int(gdf.loc[i, 'FLOOR'])) / gdf.loc[i, 'ZY_AREA'] * 100
            gdf.loc[i, 'PERCENT_CONSTRUCTION'] = percent_build
            percent_table_prev = 0.0
            for percent_table in criteria[0]['physical_aspect']['percentage_of_construction']:
                if float(percent_build) > percent_table_prev and float(percent_build) <= float(percent_table):
                    gdf.loc[i, 'SCORE_PERCENT_CONSTRUCTION'] = criteria[0]['physical_aspect']['percentage_of_construction'][percent_table]      
                percent_table_prev = float(percent_table)
        return(gdf)
    
    def alarm(gdf):
        for i in range(len(gdf)):
            if gdf.loc[i,'PR_ALARM'] == 'да':
                gdf.loc[i,'SCORE_ALARM'] = 0
            else:
                gdf.loc[i,'SCORE_ALARM'] = 1
        return(gdf)
    
    def actual_usage(gdf):
        for i in gdf.index:
            if gdf.loc[i, 'BLD_ACUSE'] == 1: # испоользуется сейчас
                gdf.loc[i, 'SCORE_BLD_ACUSE'] = 1
            elif gdf.loc[i, 'BLD_ACUSE'] == 2:
                gdf.loc[i, 'SCORE_BLD_ACUSE'] = 0.5
            elif gdf.loc[i, 'BLD_ACUSE'] == 3: # более 1 года
                gdf.loc[i, 'SCORE_BLD_ACUSE'] = 0
        return(gdf)


    def recover_engineering_communications(gdf):
        gdf['HOT_WATER'] = 1
        gdf['COLD_WATER'] = 1
        gdf['ELCTRICITY'] = 1
        gdf['SEWERAGE'] = 1
        gdf['FIRE_SYSTEM'] = 1
        for i in range(len(gdf)):
            
            if gdf.loc[i,'WEAR_PRCNT'] > 0.8:
                gdf.loc[i,'HOT_WATER'] = 0
                gdf.loc[i,'COLD_WATER'] = 1
                gdf.loc[i,'ELCTRICITY'] = 1
                gdf.loc[i,'SEWERAGE'] = 0
                gdf.loc[i,'FIRE_SYSTEM'] = 0
            elif gdf.loc[i,'WEAR_PRCNT'] <= 0.8 and gdf.loc[i,'WEAR_PRCNT'] >= 0.7:
                gdf.loc[i,'HOT_WATER'] = 0
                gdf.loc[i,'COLD_WATER'] = 1
                gdf.loc[i,'ELCTRICITY'] = 1
                gdf.loc[i,'SEWERAGE'] = 1
                gdf.loc[i,'FIRE_SYSTEM'] = 0
    
            if gdf.loc[i,'SCORE_ALARM'] == 0:
                gdf.loc[i,'HOT_WATER'] = 0
                gdf.loc[i,'COLD_WATER'] = 0
                gdf.loc[i,'ELCTRICITY'] = 0
                gdf.loc[i,'SEWERAGE'] = 0
                gdf.loc[i,'FIRE_SYSTEM'] = 0
        
        if gdf.loc[i, 'BLD_ACUSE'] == 2 or gdf.loc[i, 'BLD_ACUSE'] == 3:
                gdf.loc[i,'HOT_WATER'] = 0
                gdf.loc[i,'COLD_WATER'] = 0
                gdf.loc[i,'ELCTRICITY'] = 0
                gdf.loc[i,'SEWERAGE'] = 0
                gdf.loc[i,'FIRE_SYSTEM'] = 0
        return(gdf)



    def start_all(gdf):

        # Оценка износа здания
        gdf['SCORE_WEAR_PRCNT'] = 1 - gdf['WEAR_PRCNT']
        gdf = AspectPhysical.material(gdf)
        gdf = AspectPhysical.bld_usage(gdf)
        gdf = AspectPhysical.percentage_of_construction(gdf)
        gdf = AspectPhysical.alarm(gdf)
        gdf = AspectPhysical.recover_engineering_communications(gdf)
        gdf = AspectPhysical.actual_usage(gdf)
        gdf['SCORE_ENG_COM'] = gdf['HOT_WATER'] * 0.2 + gdf['COLD_WATER'] * 0.2 + gdf['ELCTRICITY'] * 0.2 + gdf['SEWERAGE'] * 0.2 + gdf['FIRE_SYSTEM'] * 0.2

        # Итоговый бал по аспекту
        gdf['TOTAL_ASPECT_PHYSICAL'] = round(0.25 * gdf['SCORE_WEAR_PRCNT'] + 0.13 * gdf['SCORE_MATERIAL'] + 0.10 * gdf['SCORE_BLD_USAGE'] + 0.05 * gdf['SCORE_PERCENT_CONSTRUCTION']  + 0.09 * gdf['SCORE_ALARM'] + 0.15 * gdf['SCORE_ENG_COM'] + 0.23 * gdf['SCORE_BLD_ACUSE'], 2)
        #gdf['total_physical_percent'] = round(gdf['total_physical_score'] / 8 * 100, 2) DELETE
        return(gdf)

class AspectSpatial:

# get isochrones and calculate services

    def graph_creator(gdf,territory):
        # Generating a walking graph for the defined boundary.
        G_walk = get_walk_graph(polygon=territory.geometry[0])
        return(G_walk)

    def iso_create(gdf, G_walk):
            gdf = gdf.to_crs(G_walk.graph['crs'])
            gdf['geometry'] = gdf['geometry'].centroid
            isochrones, stops, routes = get_accessibility_isochrones(
                    isochrone_type='ways',
                    points= gdf,
                    weight_type="time_min",
                    weight_value=10,
                    nx_graph=G_walk
                    )
            isochrones.drop_duplicates(inplace=True)
            return(isochrones)


    def services(gdf, shop, cafe, public_transport, isochrones):
        gdf['SCORE_SERVICES'] = 0.0
        isochrones['geometry'] = isochrones['geometry'].buffer(50)
        for i in gdf.index:
            try:
                        gdf.loc[i, 'count_shop'] = len(shop[shop.geometry.within(isochrones.geometry[i])])
            except AttributeError:
                        gdf.loc[i, 'count_shop'] = 0
            try:
                        gdf.loc[i, 'count_cafe'] = len(cafe[cafe.geometry.within(isochrones.geometry[i])])
            except AttributeError:
                        gdf.loc[i, 'count_cafe'] = 0
            try:
                        gdf.loc[i, 'count_public_transport'] = len(public_transport[public_transport.geometry.within(isochrones.geometry[i])])
            except AttributeError:
                        gdf.loc[i, 'count_public_transport'] = 0

        for i in gdf.index:
            if gdf.loc[i, 'count_shop'] >=1:
                gdf.loc[i,'SCORE_SERVICES'] += 0.5
            
            if gdf.loc[i, 'count_cafe'] >=1:
                gdf.loc[i,'SCORE_SERVICES'] += 0.5
            
            if gdf.loc[i, 'count_public_transport'] >=2:
                gdf.loc[i,'SCORE_TRANSPORT'] = 1

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
            hex.loc[i, 'count_shop'] = grouped_values['amenity'].count()
            grouped_values['amenity'] = 0

            # Выбор точек внутри полигона
            points_within_polygon = public_transport[public_transport.geometry.within(hex.geometry[i])]
            # Группировка значений
            grouped_values = points_within_polygon.groupby('osmid')['amenity'].count().reset_index()
            hex.loc[i, 'count_public_transport'] = grouped_values['amenity'].count()
            grouped_values['amenity'] = 0
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
        gdf['SCORE_HISTORICITY'] = 0.0
        for i in range(len(gdf_vision)):
            try:
                selection_buildings = gpd.overlay(building_osm, gdf_vision[gdf_vision.index == i], how='intersection')

                if selection_buildings['_culture_heritage'].count() >= 1:
                    gdf.loc[i, 'SCORE_HISTORICITY'] += 0.1
                floor_mean = selection_buildings['_building_floor'].fillna(1).astype(int).mean()
                if float(gdf.loc[i, 'FLOOR']) > float(floor_mean - 1) and float(gdf.loc[i, 'FLOOR']) < float(floor_mean + 1):
                    gdf.loc[i, 'SCORE_HISTORICITY'] += 0.3
                year_mean = selection_buildings['_building_year'].fillna(1917).astype(int).mean()
                if gdf.loc[i, 'DATE_BUILD'] > (year_mean - 20) and gdf.loc[i, 'DATE_BUILD'] < (year_mean + 20):
                    gdf.loc[i, 'SCORE_HISTORICITY'] += 0.3
            except NotImplementedError:
                gdf.loc[i, 'SCORE_HISTORICITY'] += 0.1
        return(gdf)
    
    def score_spatial(gdf):
        gdf['SCORE_SERVICES'] = 0.0
        gdf['SCORE_TRANSPORT'] = 0.0
        for i in range(len(gdf)):
            if gdf.loc[i, 'count_shop'] >=1:
                gdf.loc[i,'SCORE_SERVICES'] += 0.5
            
            if gdf.loc[i, 'count_cafe'] >=1:
                gdf.loc[i,'SCORE_SERVICES'] += 0.5
            
            if gdf.loc[i, 'count_public_transport'] >=2:
                gdf.loc[i,'SCORE_TRANSPORT'] += 1
        return(gdf)

    def start_all(gdf,territory, shop, cafe, public_transport,building, isochrones, gdf_vision):
        # Generating a walking graph for the defined boundary.
        gdf = gdf.to_crs('EPSG:32637')
        building = building.to_crs('EPSG:32637')
        building = building[building.geometry.type == 'Polygon']
        building = DataPreparation.merge_reestr_building(gdf, building)
        cafe = cafe.to_crs('EPSG:32637')
        shop = shop.to_crs('EPSG:32637')
        public_transport = public_transport.to_crs('EPSG:32637')
        isochrones = isochrones.to_crs('EPSG:32637')
        gdf_vision = gdf_vision.to_crs('EPSG:32637')
        gdf_vision = gdf_vision.to_crs('EPSG:32637')
        gdf_vision['geometry'] = gdf_vision['geometry'].buffer(35)


        gdf = AspectSpatial.services(gdf, shop, cafe, public_transport, isochrones)
        gdf = AspectSpatial.view_selection(gdf_vision,building,gdf)
        # Итоговый бал по аспекту
        gdf = gdf.fillna(0)
        gdf['TOTAL_ASPECT_SPATIAL'] = 0.06 * gdf['SCORE_SERVICES'] + 0.42 * gdf['SCORE_TRANSPORT'] + 0.52 * gdf['SCORE_HISTORICITY']
        #gdf['total_spatial_percent'] = round(gdf['total_spatial_score'] / 4 * 100, 2)
        return(gdf)
    


class AspectEconomic:
    def cad_cost_estimation_building(gdf):
        for i in range(len(gdf)):
            cad_cost = gdf.loc[i, 'BUILD_KADCOST']
            if cad_cost == 0:
                q = 'q3'
            elif cad_cost <= gdf['BUILD_KADCOST'].quantile(q = 0.25):
                q = 'q1'
            elif cad_cost <= gdf['BUILD_KADCOST'].quantile(q = 0.50):
                q = 'q2'
            elif cad_cost <= gdf['BUILD_KADCOST'].quantile(q = 0.75):
                q = 'q3'
            else:
                q = 'q4'
            gdf.loc[i, 'SCORE_BUILD_KADCOST'] = criteria[0]['economic_aspect']['cadstral_value_building'][q]
        return(gdf)

    def cad_cost_estimation_land(gdf):
        for i in range(len(gdf)):
            cad_cost = gdf.loc[i, 'ZY_KADCOST']
            if cad_cost <= 2:
                q = 'q3'
            elif cad_cost <= gdf['ZY_KADCOST'].quantile(q = 0.25):
                q = 'q1'
            elif cad_cost <= gdf['ZY_KADCOST'].quantile(q = 0.50):
                q = 'q2'
            elif cad_cost <= gdf['ZY_KADCOST'].quantile(q = 0.75):
                q = 'q3'
            else:
                q = 'q4'
            gdf.loc[i, 'SCORE_ZY_KADCOST'] = criteria[0]['economic_aspect']['cadstral_value_land'][q]
        return(gdf)
    
    def support_program(gdf):
        for i in gdf.index:
            count = 0
            if gdf.loc[i,'MATERIAL'] == 'wood':
                count += 1
            if gdf.loc[i,'PR_ALARM'] == 'да':
                count += 1
            if gdf.loc[i, 'UNESCO_TYPE'] == 'да':
                count += 1

            gdf.loc[i, 'SCORE_SUPPROGRAMS'] = criteria[0]['economic_aspect']['support_measures'][str(count)]
        return(gdf)
    
    def start_all(gdf):
        gdf=AspectEconomic.cad_cost_estimation_building(gdf)
        gdf=AspectEconomic.cad_cost_estimation_land(gdf)
        gdf=AspectEconomic.support_program(gdf)

        # Итоговый бал по аспекту
        gdf['TOTAL_ASPECT_ECONOMIC'] = 0.125 * gdf['SCORE_BUILD_KADCOST'] + 0.125 * gdf['SCORE_ZY_KADCOST'] + 0.75 * gdf['SCORE_SUPPROGRAMS']
        #gdf['total_economic_percent'] = round(gdf['total_economic_score'] / 4.22 * 100, 2) delete
        return(gdf)

class General:
    def calculate_scores(gdf):
        gdf['TOTAL_SCORE'] = gdf['TOTAL_ASPECT_LAW'] + gdf['TOTAL_ASPECT_PHYSICAL'] + gdf['TOTAL_ASPECT_SPATIAL'] + gdf['TOTAL_ASPECT_ECONOMIC']
        #gdf['total_percent'] = round(gdf['total_score'] / 20.22 * 100, 2) DELETE
        return(gdf)

    def calculate_scores_1(gdf):
        gdf['total_physical_score'] = gdf['score_percentage_of_construction'] + gdf['score_material'] + gdf['score_function'] + gdf['score_deterioration'] + gdf['score_accident']
        gdf['total_spatial_score'] = 0
        gdf['total_law_score'] = gdf['score_cadastral_integrity'] + gdf['score_land_use'] + gdf['score_protection']
        gdf['total_economic_score'] = gdf['score_cadstral_value_building'] + gdf['score_cadstral_value_land']
        gdf['total_score'] = gdf['total_physical_score'] + gdf['total_spatial_score'] + gdf['total_law_score'] + gdf['total_economic_score']
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