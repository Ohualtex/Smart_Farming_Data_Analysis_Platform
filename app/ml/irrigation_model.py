"""
Irrigation Optimization Model (RandomForest)
==============================================
ML service class that predicts required irrigation volume (litres) from
soil moisture, soil temperature, ambient humidity, ambient temperature,
and recent precipitation.

On first start: if a pickle exists under `app/ml/models/` it is loaded;
otherwise the model is re-trained on synthetic data with a deterministic
seed (42) and persisted.

---

Toprak nemi, sıcaklık, hava nemi, dış sıcaklık ve yağışı alıp gereken
sulama miktarını (litre) tahmin eder. Pickle yoksa deterministic seed
ile yeniden eğitilir.
"""

import os

import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler


class IrrigationOptimizer:
    """
    Basit Sulama Optimizasyon Modeli
    Toprak nemi ve hava durumu verilerini kullanarak
    gereken sulama miktarini tahmin eder.
    """

    # ─── Sınıf seviyesinde sabitler (magic number temizliği) ─────
    IRRIGATION_THRESHOLD_LITERS: float = 5.0  # altında "sulama gerekmiyor"
    LIGHT_IRRIGATION_LITERS: float = 20.0  # < 20 L: hafif
    MODERATE_IRRIGATION_LITERS: float = 50.0  # < 50 L: orta, ≥ 50 L: acil
    OPTIMAL_MOISTURE_PERCENT: float = 50.0  # ideal toprak nemi
    CONFIDENCE_BASE: float = 0.7
    CONFIDENCE_CAP: float = 0.95
    CONFIDENCE_MOISTURE_DIVISOR: float = 200.0

    # Synthetic training parametreleri
    N_TRAINING_SAMPLES: int = 1000
    RANDOM_SEED: int = 42
    RF_N_ESTIMATORS: int = 100
    RF_MAX_DEPTH: int = 10

    def __init__(self, model_path: str = "app/ml/models/") -> None:
        self.model_path = model_path
        self.model = None
        self.scaler = StandardScaler()
        self._initialize_model()

    def _initialize_model(self) -> None:
        model_file = os.path.join(self.model_path, "irrigation_model.pkl")
        if os.path.exists(model_file):
            self.model = joblib.load(model_file)
            self.scaler = joblib.load(os.path.join(self.model_path, "scaler.pkl"))
        else:
            self._train_with_synthetic_data()

    def _train_with_synthetic_data(self) -> None:
        np.random.seed(self.RANDOM_SEED)
        n_samples = self.N_TRAINING_SAMPLES

        soil_moisture = np.random.uniform(10, 90, n_samples)
        soil_temp = np.random.uniform(5, 40, n_samples)
        humidity = np.random.uniform(20, 95, n_samples)
        air_temp = np.random.uniform(0, 45, n_samples)
        precipitation = np.random.uniform(0, 30, n_samples)

        water_needed = np.maximum(
            0,
            (
                (50 - soil_moisture) * 2.0
                + (air_temp - 20) * 1.5
                - precipitation * 3.0
                - (humidity - 50) * 0.5
                + np.random.normal(0, 5, n_samples)
            ),
        )

        x_features = np.column_stack([soil_moisture, soil_temp, humidity, air_temp, precipitation])
        x_scaled = self.scaler.fit_transform(x_features)

        self.model = RandomForestRegressor(
            n_estimators=self.RF_N_ESTIMATORS,
            random_state=self.RANDOM_SEED,
            max_depth=self.RF_MAX_DEPTH,
        )
        self.model.fit(x_scaled, water_needed)

        os.makedirs(self.model_path, exist_ok=True)
        joblib.dump(self.model, os.path.join(self.model_path, "irrigation_model.pkl"))
        joblib.dump(self.scaler, os.path.join(self.model_path, "scaler.pkl"))

    def predict(
        self,
        soil_moisture: float,
        soil_temperature: float,
        humidity: float,
        temperature: float,
        precipitation: float,
    ) -> dict:
        features = np.array([[soil_moisture, soil_temperature, humidity, temperature, precipitation]])
        features_scaled = self.scaler.transform(features)
        predicted_water = float(self.model.predict(features_scaled)[0])
        predicted_water = max(0, round(predicted_water, 2))

        irrigation_needed = predicted_water > self.IRRIGATION_THRESHOLD_LITERS
        confidence = min(
            self.CONFIDENCE_CAP,
            self.CONFIDENCE_BASE
            + (abs(self.OPTIMAL_MOISTURE_PERCENT - soil_moisture) / self.CONFIDENCE_MOISTURE_DIVISOR),
        )

        if not irrigation_needed:
            message = "Toprak nemi yeterli, sulama gerekmiyor."
        elif predicted_water < self.LIGHT_IRRIGATION_LITERS:
            message = f"Hafif sulama oneriliyor: {predicted_water} litre."
        elif predicted_water < self.MODERATE_IRRIGATION_LITERS:
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
