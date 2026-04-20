"""
AutoSense – AI-Based Vehicle Health Monitoring System
Module  : Fault Injector
File    : fault_injector.py
Path    : C:/Users/hrish/AutoSense/backend/modules/fault_injector.py
Purpose : Injects realistic, randomised faults into a telemetry data
          dictionary to simulate real-world vehicle fault conditions.

Fault probability:
    70% → No fault injected  (normal driving)
    30% → Fault(s) injected  → 80% single fault / 20% multiple faults

Supported fault types:
    1. Overheating       – Raises coolant temperature
    2. Engine Stress     – Spikes RPM and engine load
    3. Overspeed         – Sets vehicle speed above safe limit
    4. Battery Drop      – Drops control module voltage (min 9 V)
    5. Intake Issue      – Raises intake air temperature
    6. Fuel Mixture      – Shifts fuel-air ratio lean or rich

Usage:
    from modules.fault_injector import FaultInjector

    fi   = FaultInjector()
    result = fi.inject_fault(telemetry_row)
    print(result["data"])    # modified telemetry dict
    print(result["faults"])  # list of fault names, e.g. ["Overheating"]
"""

import copy
import random


# ─────────────────────────────────────────────────────────────────
# CLASS: FaultInjector
# ─────────────────────────────────────────────────────────────────

class FaultInjector:
    """
    Injects randomised vehicle faults into a telemetry data dictionary.

    Each call to inject_fault() has a 30 % chance of introducing one
    or more faults. The original dictionary is never mutated — a deep
    copy is used so the simulator's data remains clean.
    """

    # ── Probabilities (kept as class-level constants for easy tuning) ──
    FAULT_PROBABILITY   = 0.30   # overall chance a fault occurs
    MULTI_FAULT_CHANCE  = 0.20   # if fault occurs: chance of MULTIPLE faults

    def __init__(self):
        """
        Build the fault registry.

        Each entry maps a human-readable fault name to the private
        handler method that applies it. Storing them in a dict lets us
        randomly sample one or many faults cleanly.
        """
        # Registry: fault_name → method reference
        self._fault_handlers = {
            "Overheating"       : self._fault_overheating,
            "Engine Stress"     : self._fault_engine_stress,
            "Overspeed"         : self._fault_overspeed,
            "Battery Drop"      : self._fault_battery_drop,
            "Intake Issue"      : self._fault_intake_issue,
            "Fuel Mixture Issue": self._fault_fuel_mixture,
        }

        print("[FaultInjector] Initialised with "
              f"{len(self._fault_handlers)} fault type(s) registered.")

    # ─────────────────────────────────────────────────────────────
    # PUBLIC METHOD: inject_fault
    # ─────────────────────────────────────────────────────────────

    def inject_fault(self, data: dict) -> dict:
        """
        Possibly inject one or more faults into the telemetry data.

        Args:
            data (dict): A single row of vehicle telemetry produced
                         by VehicleSimulator.get_next_data().

        Returns:
            dict: {
                "data"  : dict  – telemetry dict (modified or unchanged),
                "faults": list  – names of injected faults (empty if none)
            }
        """
        # Always work on a copy — never mutate the original row
        modified_data  = copy.deepcopy(data)
        injected_faults = []

        # ── 70 % chance: do nothing ───────────────────────────────
        if random.random() > self.FAULT_PROBABILITY:
            return {"data": modified_data, "faults": injected_faults}

        # ── Decide: single fault or multiple faults ───────────────
        all_fault_names = list(self._fault_handlers.keys())

        if random.random() < self.MULTI_FAULT_CHANCE:
            # Multiple faults: pick between 2 and (total available) faults
            num_faults  = random.randint(2, len(all_fault_names))
            chosen_faults = random.sample(all_fault_names, num_faults)
        else:
            # Single fault: pick exactly one
            chosen_faults = [random.choice(all_fault_names)]

        # ── Apply each chosen fault handler in sequence ───────────
        for fault_name in chosen_faults:
            handler = self._fault_handlers[fault_name]
            modified_data = handler(modified_data)
            injected_faults.append(fault_name)

        return {"data": modified_data, "faults": injected_faults}

    # ─────────────────────────────────────────────────────────────
    # PRIVATE FAULT HANDLERS
    # Each method receives the data dict, modifies a copy, returns it.
    # ─────────────────────────────────────────────────────────────

    def _fault_overheating(self, data: dict) -> dict:
        """
        Overheating fault.
        Simulates a failing cooling system by spiking coolant temperature.

        Column affected : coolant_temp_ (or coolant_temperature_)
        Change          : +20 to +40 °C
        """
        # Support both possible column name variants in the dataset
        key = self._find_key(data, ["coolant_temp_", "coolant_temperature_"])
        if key:
            data[key] = data[key] + random.uniform(20, 40)
        return data

    def _fault_engine_stress(self, data: dict) -> dict:
        """
        Engine Stress fault.
        Simulates aggressive driving or mechanical strain by raising
        engine RPM and engine load simultaneously.

        Columns affected:
            engine_rpm_   → +1000 to +3000 RPM
            engine_load_  → +20  to +40 %
        """
        key_rpm  = self._find_key(data, ["engine_rpm_", "engine_rpm"])
        key_load = self._find_key(data, ["engine_load_", "engine_load",
                                         "calculated_engine_load_"])
        if key_rpm:
            data[key_rpm]  = data[key_rpm]  + random.uniform(1000, 3000)
        if key_load:
            # Engine load is typically 0–100 %; cap at 100
            data[key_load] = min(100.0, data[key_load] + random.uniform(20, 40))
        return data

    def _fault_overspeed(self, data: dict) -> dict:
        """
        Overspeed fault.
        Simulates reckless acceleration by setting vehicle speed to a
        dangerously high value.

        Column affected : vehicle_speed_  → set to 120–160 km/h
        """
        key = self._find_key(data, ["vehicle_speed_", "vehicle_speed"])
        if key:
            data[key] = random.uniform(120, 160)
        return data

    def _fault_battery_drop(self, data: dict) -> dict:
        """
        Battery Drop fault.
        Simulates a weak or failing battery / alternator by reducing
        the control module voltage.

        Column affected : control_module_voltage_  → -2 to -4 V
        Minimum allowed : 9 V  (below this the ECU would shut down)
        """
        key = self._find_key(data, ["control_module_voltage_",
                                    "control_module_voltage"])
        if key:
            dropped = data[key] - random.uniform(2, 4)
            # Clamp to a realistic minimum — ECU behaviour below 9 V is undefined
            data[key] = max(9.0, dropped)
        return data

    def _fault_intake_issue(self, data: dict) -> dict:
        """
        Intake Air Issue fault.
        Simulates a clogged air filter or turbo problem by raising the
        intake air temperature.

        Column affected : intake_air_temp_  → +15 to +30 °C
        """
        key = self._find_key(data, ["intake_air_temp_", "intake_air_temperature_",
                                    "intake_air_temp"])
        if key:
            data[key] = data[key] + random.uniform(15, 30)
        return data

    def _fault_fuel_mixture(self, data: dict) -> dict:
        """
        Fuel Mixture Issue fault.
        Simulates a faulty fuel injector or O2 sensor by pushing the
        commanded fuel–air equivalence ratio either lean (<1) or rich (>1).

        Column affected : fuel_air_commanded_equiv_ratio_
        Lean  band      : 0.6 – 0.8   (too little fuel)
        Rich  band      : 1.2 – 1.5   (too much fuel)
        """
        key = self._find_key(data, ["fuel_air_commanded_equiv_ratio_",
                                    "commanded_equiv_ratio_",
                                    "fuel_air_commanded_equiv_ratio"])
        if key:
            # Randomly choose lean or rich mixture
            if random.random() < 0.5:
                data[key] = random.uniform(0.6, 0.8)   # lean
            else:
                data[key] = random.uniform(1.2, 1.5)   # rich
        return data

    # ─────────────────────────────────────────────────────────────
    # HELPER METHOD: _find_key
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def _find_key(data: dict, candidates: list) -> str | None:
        """
        Return the first key from `candidates` that exists in `data`.

        This makes each fault handler resilient to minor column name
        variations across different versions of the cleaned dataset.

        Args:
            data       (dict): The telemetry dictionary to search.
            candidates (list): Ordered list of possible key names.

        Returns:
            str  : The matching key name, or
            None : If none of the candidates are present in data.
        """
        for key in candidates:
            if key in data:
                return key
        # Warn once so the developer knows a column is missing
        print(f"[FaultInjector] WARNING: None of {candidates} found in data. "
              "Fault skipped.")
        return None


# ─────────────────────────────────────────────────────────────────
# QUICK TEST – runs only when this file is executed directly
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Minimal synthetic telemetry row that mirrors cleaned_data.csv columns
    sample_data = {
        "engine_rpm_"                      : 1500.0,
        "vehicle_speed_"                   : 60.0,
        "coolant_temp_"                    : 85.0,
        "engine_load_"                     : 45.0,
        "control_module_voltage_"          : 14.2,
        "intake_air_temp_"                 : 35.0,
        "fuel_air_commanded_equiv_ratio_"  : 1.0,
    }

    fi = FaultInjector()

    print("\n" + "=" * 55)
    print("  AutoSense — FaultInjector Quick Test (10 rounds)")
    print("=" * 55)

    for i in range(1, 11):
        result = fi.inject_fault(sample_data)
        faults = result["faults"] if result["faults"] else ["None"]
        print(f"\nRound {i:>2} | Faults: {', '.join(faults)}")

        # Show only the values that changed
        for key in sample_data:
            original = sample_data[key]
            modified = result["data"][key]
            if round(original, 4) != round(modified, 4):
                print(f"    {key:<45} : {original:.2f}  →  {modified:.2f}")
