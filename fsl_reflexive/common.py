"""RRAO validation primitives. Apache-2.0."""
from datetime import date, datetime, time, timezone
from fractions import Fraction
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parent.parent
SHA = re.compile(r"[a-f0-9]{64}\Z")
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")


class RRAOError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise RRAOError(message)


def exact(x, keys, where):
    require(isinstance(x, dict) and set(x) == set(keys),
            f"{where}: missing or unknown fields")


def choice(x, values, where):
    require(isinstance(x, str) and x in values, f"{where}: invalid choice")


def ident(x, where, nullable=False):
    require((nullable and x is None) or (isinstance(x, str) and ID.fullmatch(x)),
            f"{where}: invalid identifier")


def sha(x, where, nullable=False):
    require((nullable and x is None) or (isinstance(x, str) and SHA.fullmatch(x)),
            f"{where}: invalid SHA-256")


def integer(x, where, nullable=False, minimum=0):
    require((nullable and x is None) or (type(x) is int and x >= minimum),
            f"{where}: invalid count")


def boolean(x, where, nullable=False):
    require((nullable and x is None) or type(x) is bool, f"{where}: boolean required")


def nonempty(x, where, nullable=False):
    require((nullable and x is None) or (isinstance(x, str) and 0 < len(x.strip()) <= 2048),
            f"{where}: empty or invalid string")


def unique_pairs(pairs):
    out = {}
    for k, v in pairs:
        require(k not in out, f"duplicate JSON key: {k}")
        out[k] = v
    return out


def load_json(path):
    def bad(x):
        raise RRAOError(f"non-finite JSON number: {x}")
    return json.loads(Path(path).read_text(encoding="utf-8"),
                      object_pairs_hook=unique_pairs, parse_constant=bad)


def timestamp(x, cutoff=False):
    require(isinstance(x, str), "timestamp string required")
    try:
        if cutoff and re.fullmatch(r"\d{4}-\d{2}-\d{2}", x):
            return datetime.combine(date.fromisoformat(x), time.max, timezone.utc)
        require("T" in x, "timestamp must include time")
        t = datetime.fromisoformat(x.replace("Z", "+00:00"))
        require(t.tzinfo is not None and t.utcoffset() is not None,
                "timestamp must include offset")
        return t.astimezone(timezone.utc)
    except (ValueError, OverflowError) as exc:
        raise RRAOError(f"invalid timestamp: {x}") from exc


def ratio(n, d):
    return None if n is None or d is None or d == 0 else Fraction(n, d)


def pack(x):
    return None if x is None else {"numerator": x.numerator, "denominator": x.denominator}


def gate(states):
    if "failed" in states:
        return "failed"
    return "unknown" if "unknown" in states else "passed"


def test_gate(x, condition):
    return "unknown" if x is None else ("passed" if condition(x) else "failed")


def le(a, b, where):
    if a is not None and b is not None:
        require(a <= b, f"{where}: exceeds bound")


def index_rows(rows, keys, idkey, where):
    require(isinstance(rows, list), f"{where}: array required")
    out = {}
    for row in rows:
        exact(row, keys, where)
        i = row[idkey]
        ident(i, idkey)
        require(i not in out, f"{where}: duplicate ID")
        out[i] = row
    return out

def signed_integer(x, where, nullable=False):
    require((nullable and x is None) or type(x) is int, f"{where}: integer required")


def bps(x, where, nullable=True, capped=True):
    integer(x, where, nullable=nullable)
    if x is not None and capped:
        require(x <= 10000, f"{where}: basis points exceed 10000")


def numeric_fields(obj, keys, signed=()):
    for k in keys:
        (signed_integer if k in signed else integer)(obj[k], k, nullable=True)


def bounded_list(xs, where, low=1, high=120):
    require(isinstance(xs,list) and low <= len(xs) <= high, f"{where}: array size {low}..{high}")


def assumption(d, field="assumed"):
    boolean(d[field],field)
    return d[field]
