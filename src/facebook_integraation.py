# src/facebook_integration.py
import pandas as pd
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.targeting import Targeting

def generate_ad_suggestions(top5_df, access_token, ad_account_id):
    FacebookAdsApi.init(access_token=access_token)
    suggestions = []
    for _, row in top5_df.iterrows():
        targeting = Targeting()
        targeting[Targeting.Field.genders] = [1 if row['Male_%'] > row['Female_%'] else 2]  # 1=Male, 2=Female
        targeting[Targeting.Field.age_min] = int(row['Top_Age_Group'].split('-')[0]) if '-' in row['Top_Age_Group'] else 18
        targeting[Targeting.Field.age_max] = int(row['Top_Age_Group'].split('-')[1]) if '-' in row['Top_Age_Group'] else 65
        targeting[Targeting.Field.regions] = [{'key': 'TN'}]  # Tunisia
        suggestions.append({
            'Product': row['Product'],
            'Suggested_Targeting': targeting.export_all_data()
        })
    return pd.DataFrame(suggestions)