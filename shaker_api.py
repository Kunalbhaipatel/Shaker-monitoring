from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pandas as pd
import numpy as np
from io import StringIO

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/analyze")
async def analyze_csv(file: UploadFile = File(...), reset_life: bool = False, failure_threshold: int = 30):
    try:
        contents = await file.read()
        df = pd.read_csv(StringIO(contents.decode("utf-8")), low_memory=False)
        df.replace(-999.25, np.nan, inplace=True)

        df['SHAKER Output'] = df.get('SHAKER #1 (Units)', 0).fillna(0) + df.get('SHAKER #2 (Units)', 0).fillna(0)
        df['G-Force Drop Alert'] = np.where(
            (df['SHAKER Output'] < df['SHAKER Output'].rolling(10, min_periods=1).mean()) &
            (df['Rate Of Penetration (ft_per_hr)'] > 0), "⚠️ Potential Drop", "✅ Normal")

        df['Solids Load'] = df['Rate Of Penetration (ft_per_hr)'] * np.pi * (8.5/12)**2 / 4
        df['Screen Capacity'] = 200
        df['Screen Utilization (%)'] = (df['Solids Load'] / df['Screen Capacity']) * 100

        df['Time on Bottom (hrs)'] = df['On Bottom Hours (hrs)'].fillna(method='ffill')
        df['MSE'] = df['Mechanical Specific Energy (ksi)'].fillna(method='ffill')
        df['Screen Life Used (%)'] = ((df['MSE'] * df['Time on Bottom (hrs)']) / 5000).clip(0, 100)

        df['Circulating Hours'] = df['Circulating Hours (hrs)'].fillna(method='ffill')
        df['Vibration Stress Index'] = (df['SHAKER Output'] / df['SHAKER Output'].max()).fillna(0)
        df['Thermal Factor'] = (df['tgs Box Temperature (deg_f)'] / 180).clip(0, 1).fillna(0)

        df['Shaker Life Used (%)'] = (
            0.5 * (df['Circulating Hours'] / 10000) +
            0.3 * df['Vibration Stress Index'] +
            0.2 * df['Thermal Factor']
        ) * 100

        if reset_life:
            df['Shaker Life Used (%)'] = 0

        df['Shaker Life Used (%)'] = df['Shaker Life Used (%)'].clip(0, 100)
        df['Shaker Life Remaining (%)'] = 100 - df['Shaker Life Used (%)']

        result = {
            "Screen Utilization (%)": round(df['Screen Utilization (%)'].iloc[-1], 2),
            "Screen Life Remaining (%)": round(100 - df['Screen Life Used (%)'].iloc[-1], 2),
            "Shaker Life Remaining (%)": round(df['Shaker Life Remaining (%)'].iloc[-1], 2),
            "G-Force Drop Alert": df['G-Force Drop Alert'].iloc[-1],
            "Shaker Status": "🔴 At Risk" if df['Shaker Life Remaining (%)'].iloc[-1] < failure_threshold else "🟢 OK"
        }
        return JSONResponse(content=result)

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
