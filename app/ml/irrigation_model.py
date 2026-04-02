import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import joblib
import os


class IrrigationOptimizer:
    """
    Basit Sulama Optimizasyon Modeli
    Toprak nemi ve hava durumu verilerini kullanarak
    gereken sulama miktarini tahmin eder.
    """

    def __init__(self, model_path="app/ml/models/"):
        self.model_path = model_path
        self.model = None
        self.scaler = StandardScaler()
        self._initialize_model()

    def _initialize_model(self):
        model_file = os.path.join(self.model_path, "irrigation_model.pkl")
        if os.path.exists(model_file):
            self.model = joblib.load(model_file)
            self.scaler = joblib.load(os.path.join(self.model_path, "scaler.pkl"))
        else:
            self._train_with_synthetic_data()

    def _train_with_synthetic_data(self):
        np.random.seed(42)
        n_samples = 1000

        soil_moisture = np.random.uniform(10, 90, n_samples)
        soil_temp = np.random.uniform(5, 40, n_samples)
        humidity = np.random.uniform(20, 95, n_samples)
        air_temp = np.random.uniform(0, 45, n_samples)
        precipitation = np.random.uniform(0, 30, n_samples)

        water_needed = np.maximum(0, (
            (50 - soil_moisture) * 2.0
            + (air_temp - 20) * 1.5
            - precipitation * 3.0
            - (humidity - 50) * 0.5
            + np.random.normal(0, 5, n_samples)
        ))

        X = np.column_stack([soil_moisture, soil_temp, humidity, air_temp, precipitation])
        X_scaled = self.scaler.fit_transform(X)

        self.model = RandomForestRegressor(n_estimators=100, random_state=42, max_depth=10)
        self.model.fit(X_scaled, water_needed)

        os.makedirs(self.model_path, exist_ok=True)
        joblib.dump(self.model, os.path.join(self.model_path, "irrigation_model.pkl"))
        joblib.dump(self.scaler, os.path.join(self.model_path, "scaler.pkl"))

    def predict(self, soil_moisture, soil_temperature, humidity, temperature, precipitation):
        features = np.array([[soil_moisture, soil_temperature, humidity, temperature, precipitation]])
        features_scaled = self.scaler.transform(features)
        predicted_water = float(self.model.predict(features_scaled)[0])
        predicted_water = max(0, round(predicted_water, 2))

        irrigation_needed = predicted_water > 5.0
        confidence = min(0.95, 0.7 + (abs(50 - soil_moisture) / 200))

        if not irrigation_needed:
            message = "Toprak nemi yeterli, sulama gerekmiyor."
        elif predicted_water < 20:
            message = f"Hafif sulama oneriliyor: {predicted_water} litre."
        elif predicted_water < 50:
            message = f"Orta duzeyde sulama gerekli: {predicted_water} litre."
        else:
            message = f"Acil sulama gerekli: {predicted_water} litre!"

        return {
            "recommended_water_liters": predicted_water,
            "irrigation_needed": irrigation_needed,
            "confidence": round(confidence, 2),
            "message": message,
        }


irrigation_optimizer = IrrigationOptimizer()
