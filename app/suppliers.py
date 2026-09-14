"""Supplier registry: every supplier is classified into a money rail.

- "connect": supplier is in a Stripe-supported country and onboarded as a
  Connect (Express) account -> automatic split, destination charge or timed
  transfer.
- "manual_wire": supplier cannot onboard (mainland China, Turkey, ...).
  Buyer pays ORXYZ; ORXYZ wires the supplier after buyer funds clear, per the
  standing principal-spread doctrine. Never auto-release.
"""
from dataclasses import dataclass
from enum import Enum


class Rail(str, Enum):
    CONNECT = "connect"
    MANUAL_WIRE = "manual_wire"


# Mainland China is NOT Stripe-supported (verified 2026-09-14 against
# Stripe's global availability list). Turkey is also unsupported.
MANUAL_WIRE_COUNTRIES = {"CN", "TR"}


@dataclass
class Supplier:
    id: str
    name: str
    country: str  # ISO-2
    connect_account_id: str | None = None  # acct_... once onboarded

    @property
    def rail(self) -> Rail:
        if self.country in MANUAL_WIRE_COUNTRIES:
            return Rail.MANUAL_WIRE
        return Rail.CONNECT if self.connect_account_id else Rail.MANUAL_WIRE

    @property
    def auto_split_possible(self) -> bool:
        return self.rail is Rail.CONNECT


# Seeded from the live supplier network (2026-09-14). connect_account_id is
# filled in as each supplier completes Express onboarding.
SUPPLIERS: dict[str, Supplier] = {
    "bestok": Supplier("bestok", "BESTOK Valve (Hebei)", "CN"),
    "huade": Supplier("huade", "Beijing Huade Hydraulic", "CN"),
    "wenhan": Supplier("wenhan", "Ningbo Wenhan Fluid Equipments", "CN"),
    "gofai": Supplier("gofai", "GOFAI / cyseals", "CN"),
    "tefule": Supplier("tefule", "Shandong Tefule Bearing", "CN"),
    "norm": Supplier("norm", "Norm Fasteners", "TR"),
    "cetin": Supplier("cetin", "Cetin Civata", "TR"),
    "kaleliler": Supplier("kaleliler", "Kaleliler", "TR"),
    "conexdepot": Supplier("conexdepot", "ConexDepot (Tony Vo)", "US"),
    "chargebar": Supplier("chargebar", "ChargeBar Inc.", "US"),
    "kinzoku": Supplier("kinzoku", "Kinzoku", "JP"),
    "mgatlantic": Supplier("mgatlantic", "MG-Atlantic SA", "CH"),
    "prumex": Supplier("prumex", "Prumex s.r.o.", "CZ"),
}


def get_supplier(supplier_id: str) -> Supplier:
    try:
        return SUPPLIERS[supplier_id]
    except KeyError:
        raise ValueError(f"unknown supplier: {supplier_id}")
