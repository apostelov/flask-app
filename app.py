from flask import Flask, render_template, request, redirect, url_for, session
import requests

app = Flask(__name__)
app.secret_key = "5zli3ji59h320xyeu6bss5s9uobd2l5pio03fdbc7cb4jyy9ws"

# RDW API URL
RDW_API_URL = "https://opendata.rdw.nl/resource/m9d7-ebf2.json"

# Onderhoudswerkzaamheden en hun kosten
TASKS = {
    "oil_change": {"label": "Olie verversen", "cost": 50},
    "spark_plug_replacement": {"label": "Bougies vervangen", "cost": 75},
    "microfilter_replacement": {"label": "Microfilter vervangen", "cost": 45},
    "air_filter_replacement": {"label": "Luchtfilter vervangen", "cost": 30},
    "apk": {"label": "APK-keuring", "cost": 60},
    "fuel_filter_replacement": {"label": "Brandstoffilter vervangen", "cost": 75},
    "brake_fluid_replacement": {"label": "Remvloeistof vervangen", "cost": 90},
    "battery_remote_replacement": {"label": "Batterij afstandsbediening vervangen", "cost": 15},
    "read_error_codes": {"label": "Voertuig storingscodes uitlezen", "cost": 50},
    "brake_inspection": {"label": "Remmeninspectie en -reiniging", "cost": 25},
    "tire_inspection": {"label": "Banden inspectie", "cost": 25},
    "ac_system_check": {"label": "Controle werking aircosysteem", "cost": 15},
}

# Basisprijs (vast bedrag dat bij de kosten wordt opgeteld)
BASE_COST = 10

# Helperfunctie: voertuiggegevens ophalen
def fetch_vehicle_data(license_plate):
    try:
        license_plate = license_plate.replace(" ", "").upper()
        response = requests.get(RDW_API_URL, params={"kenteken": license_plate})
        response.raise_for_status()
        data = response.json()
        if data:
            vehicle = data[0]
            return {
                "license_plate": license_plate,
                "model": vehicle.get("handelsbenaming", "Onbekend model"),
                "year": vehicle.get("datum_eerste_toelating", "Onbekend")[:4],
                "apk_expiration": vehicle.get("vervaldatum_apk", "Onbekend"),
            }
    except Exception as e:
        print(f"Fout bij ophalen voertuiggegevens: {e}")
        return None

# Helperfunctie: kosten berekenen
def calculate_cost(work_selections):
    # Totale kosten voor geselecteerde taken
    total_task_cost = sum(
        TASKS[task]["cost"] for task, selected in work_selections.items() if selected
    )
    # Voeg de basisprijs toe
    total_cost = BASE_COST + total_task_cost
    return round(total_cost, 2)

# Helperfunctie: totale kosten incl. BTW
def calculate_total_cost(payment_option, monthly_cost):
    if payment_option == "yearly":
        return round(monthly_cost * 12 * 1.21, 2)
    return round(monthly_cost * 1.21, 2)

# Route: Onderhoudskosten calculator
@app.route("/", methods=["GET", "POST"])
def calculator():
    if request.method == "POST":
        license_plate = request.form.get("license_plate")
        vehicle_data = fetch_vehicle_data(license_plate)

        if not vehicle_data:
            return render_template(
                "calculator.html", tasks=TASKS, error="Voertuiggegevens konden niet worden opgehaald. Controleer het kenteken."
            )

        # Opslaan van gegevens in de sessie
        session["vehicle_data"] = vehicle_data
        session["work_selections"] = {
            task: request.form.get(task) == "on" for task in TASKS
        }
        session["monthly_cost"] = calculate_cost(session["work_selections"]) / 12

        return redirect(url_for("customer_info"))

    return render_template("calculator.html", tasks=TASKS, work_selections={})

# Route: Klantgegevens
@app.route("/customer-info", methods=["GET", "POST"])
def customer_info():
    if request.method == "POST":
        if "back" in request.form:  # Handle "Vorige" button
            return redirect(url_for("calculator"))

        session["customer_data"] = {
            "name": request.form.get("name"),
            "address": request.form.get("address"),
            "iban": request.form.get("iban"),
            "signature": request.form.get("signature"),
        }
        session["payment_option"] = request.form.get("payment_option")

        return redirect(url_for("summary"))

    return render_template(
        "customer_info.html",
        monthly_cost=session.get("monthly_cost"),
        yearly_cost=session.get("monthly_cost") * 12 * 1.21,
    )

# Route: Overzicht
@app.route("/summary", methods=["GET", "POST"])
def summary():
    if request.method == "POST":
        if "back" in request.form:  # Handle "Vorige" button
            return redirect(url_for("customer_info"))

    total_cost = calculate_total_cost(
        session.get("payment_option"), session.get("monthly_cost")
    )
    return render_template(
        "summary.html",
        vehicle_data=session.get("vehicle_data"),
        customer_data=session.get("customer_data"),
        payment_option=session.get("payment_option"),
        total_cost=total_cost,
        base_cost=BASE_COST,
    )

if __name__ == "__main__":
    app.run(debug=True)
