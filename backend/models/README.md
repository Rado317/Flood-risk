Place ton fichier `pipeline_random_forest.pkl`,`pipeline_regression_logistique.pkl`,`pipeline_xgboost.pkl` (Random Forest, XGBoost, etc.) ici.

Le backend le chargera automatiquement au premier appel à `/api/predict`
s'il est présent, pour ajouter la probabilité du modèle ML en complément
du seuillage direct sur `hauteur_max`.
