"""Congela los análisis huérfanos moviéndolos a una colección aparte.

Corrido el 2026-09-13 sobre los 44 huérfanos que dejó la reconstrucción
del índice de P-007; evidencia y razonamiento en
`docs/evidencia/congelamiento-analisis-huerfanos-2026-09-13.md`. Queda
en el repo porque la operación es repetible: cualquier reconstrucción
futura del índice puede volver a dejar análisis sin turno detrás.

Reversible por construcción: los documentos se COPIAN a
`analisis_huerfanos_<fecha>` y sólo se borran del origen cuando la copia
está verificada documento a documento (_id y campos). Deshacer es el
movimiento inverso, igual que el intercambio por renombrado de P-007.
"""
import sys
import pymongo

FECHA = "20260913"
DESTINO = f"analisis_huerfanos_{FECHA}"
seco = "--apply" not in sys.argv

c = pymongo.MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=3000)
db = c["skopos"]
an, tu = db["analisis"], db[DESTINO]

vivos = set(db["turnos"].distinct("turn_id"))
huerfanos = [d for d in an.find({}) if d["turn_id"] not in vivos]
ids = [d["_id"] for d in huerfanos]
print(f"analisis: {an.count_documents({})} | huerfanos a congelar: {len(huerfanos)}")
print(f"destino: skopos.{DESTINO} (existentes: {tu.count_documents({})})")
if seco:
    print("\nENSAYO — no se escribe nada. Añade --apply para ejecutar.")
    for d in huerfanos[:3]:
        print("  ", d["turn_id"][:60], "|", d.get("tema","")[:50])
    sys.exit(0)

if not huerfanos:
    print("nada que congelar"); sys.exit(0)

# 1. copiar
tu.insert_many(huerfanos, ordered=True)
# 2. verificar la copia documento a documento antes de borrar nada
faltan = [i for i in ids if tu.count_documents({"_id": i}, limit=1) == 0]
if faltan:
    print(f"ABORTA: {len(faltan)} documentos no llegaron a la copia; no se borra nada")
    sys.exit(1)
distintos = []
for d in huerfanos:
    copia = tu.find_one({"_id": d["_id"]})
    if copia != d:
        distintos.append(d["_id"])
if distintos:
    print(f"ABORTA: {len(distintos)} copias no son identicas al original; no se borra nada")
    sys.exit(1)
print(f"copia verificada: {len(ids)}/{len(ids)} documentos identicos")
# 3. retirar del origen
r = an.delete_many({"_id": {"$in": ids}})
print(f"retirados de skopos.analisis: {r.deleted_count}")
print(f"analisis ahora: {an.count_documents({})} | congelados: {tu.count_documents({})}")
