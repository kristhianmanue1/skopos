# Renovación local RS1 CTIM — 10 de octubre de 2026

Estado: ensayo local ejecutado. La evidencia operativa completa permanece bajo
`runs/ctim-rs1-draft-local-v1/renewal-2026-10-19/` (ignorado por Git).
No se copió el PDF ni se admitió al corpus. El inventario de ocho fuentes,
los siete perfiles ajenos a RS1 y los recibos históricos no se modificaron.

## Identidad y política

- Original referido: `2900-003-001_RS1.pdf` en la raíz Downloads
  preautorizada; SHA-256 `1f8ad5e506b21cbf6b568b68790d2a757ba870524a6ba341f2dff3637d2494f2`.
- Material `operator-ctim-procedure-rs1-2026-10-10`, revisión 2; procedencia
  atribuida al Operador. No se adjudica oficialidad ni vigencia jurídica.
- Política de custodia v0.3: SHA-256 canónico
  `ab17f4d51f192ca54accf08a725c783303a2f7fba82d0088311402b73cff253c`;
  recibo real
  `expertogobernanza:operator-ctim-procedure-rs1-2026-10-10:2:ba82eba90a3f642f`.
- Retención de custodia y derivados hasta `2026-10-19T16:00:00Z`, con
  `block_then_explicit_retirement`. Recuperación condicionada a que la
  referencia externa permanezca accesible y conserve los mismos bytes.
- Política documental v0.3: SHA-256 canónico
  `2498278da51ec486ae0c15185b6e7a49fadb2844e7b161f3c8941ef8d3f1a126`.

## Derivación y acceso

| Perfil | Derivación | SHA-256 del manifiesto | Cobertura |
| --- | --- | --- | --- |
| Nativo | `a302f49fc7173592ff34839a485558f01b598f64ea23a665b3e377010c35a040` | `7e0b4ba00b6ba49ac735c45545e245333ea9b4b74b239b4355378a06474680b4` | 68/68 páginas nativas |
| OCR selectivo | `834ccd8733a7f558f72cf3141d6e9cf93a32287f8bb00e6be72e3ed9b1f1cf07` | `bf564fb45128cf9859f9217b513fbf86f2f466678879d566c3ee9e9a4fcc567b` | 68/68 nativas y OCR en 22–25 |

Los manifiestos se comprobaron contra sus bytes, la revisión 2 y el nuevo
recibo. El perfil nativo de ocho fuentes tiene SHA-256 de archivo
`d05166b6566451d6c1a608a38187c2417107eeaeb94b2f5d15eb5ae5088d7c81`;
el perfil OCR, `79563c666c19c39fa2afab31029500b5e8c6251c7431136a752a8aada9c0a3e9`.
En ambos, `read_pdf_page` de la página 21 de RS1 respondió `ok` con el SHA
original, y una identidad ajena respondió `source_not_allowed` sin resultado.

En la primera ejecución nativa se produjo el manifiesto, pero faltaba el
directorio local `derived/requests` para escribir el recibo. Se creó con modo
0700 y se repitió la misma solicitud. El host reconoció el manifiesto por
identidad y hash (`derivation_status: duplicate`) y escribió el recibo real.
No se debe interpretar el primer `store_unavailable` como derivación fallida.

Verificación de código: `unittest discover -s tests -q` finalizó con 483
pruebas correctas y seis omitidas; `check_sizes.py` y `check_plans.py`
finalizaron correctamente. Los manifests tienen `fidelity_status: unreviewed`;
estas comprobaciones prueban integridad, cobertura estructural y acceso local,
no fidelidad semántica ni continuidad si desaparece el archivo externo.
