import json
# Закружаем критерии оценки
with open("Example_files/criteria.json", encoding="UTF-8") as file_in:
    criteria = json.load(file_in)

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
                percent_build = (gdf.loc[i, 'Площадь, кв.м'] / int(gdf.loc[i, 'Количество этажей (в том числе подземных)'])) / gdf.loc[i, 'area'] * 100
            gdf.loc[i, 'percentage_of_construction'] = percent_build
            percent_table_prev = 0.0
            for percent_table in criteria[0]['physical_aspect']['percentage_of_construction']:
                if float(percent_build) > percent_table_prev and float(percent_build) <= float(percent_table):
                    gdf.loc[i, 'score_percentage_of_construction'] = criteria[0]['physical_aspect']['percentage_of_construction'][percent_table]      
                percent_table_prev = float(percent_table)
        return(gdf)


    def start_all(gdf):
        # Оценка износа здания
        gdf['score_deterioration'] = 1 - gdf['Совокупный износ']
        gdf = AspectPhysical.material(gdf)
        gdf = AspectPhysical.function(gdf)
        gdf = AspectPhysical.percentage_of_construction(gdf)
        return(gdf)

class AspectSpatial:
    print()

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
    
    def start_all(gdf):
        gdf=AspectEconomic.cad_cost_estimation_building(gdf)
        gdf=AspectEconomic.cad_cost_estimation_land(gdf)
        return(gdf)

class General:
    def calculate_scores(gdf):
        gdf['total_physical_score'] = gdf['score_percentage_of_construction'] + gdf['score_material'] + gdf['score_function'] + gdf['score_deterioration']
        gdf['total_spatial_score'] = 0
        gdf['total_law_score'] = gdf['score_adastral_integrity'] + gdf['score_land_use'] + gdf['score_protection']
        gdf['total_economic_score'] = gdf['score_cadstral_value_building'] + gdf['score_cadstral_value_land']
        gdf['total_score'] = gdf['total_physical_score'] + gdf['total_spatial_score'] + gdf['total_law_score'] + gdf['total_economic_score']
        return(gdf)