# CLAUDE.md

Revisor en Python que mide la huella de IA en textos en español. Mide y marca, no reescribe.

## Comandos
```bash
uv run --group dev pytest            # pruebas, deben quedar en verde antes de cada commit
uv run humanizador archivo.docx --perfil estricto --marcar --html
```

## Reglas del proyecto
- Todo umbral sale de la calibración (`calibracion/`), no del criterio. Si se cambia uno, se vuelve a medir.
- Un falso positivo encontrado en un texto real se arregla en la regla y se agrega como prueba.
- `tests/casos/` solo lleva textos de dominio público o con licencia que permita publicarlos. Nunca
  trabajos de clase, informes de clientes ni nada con nombres de personas reales que no lo autorizaron.
- No se promete detectar IA ni pasar Turnitin. El README lo dice y se mantiene así.
- Antes de publicar cambios: pruebas en verde y revisión de seguridad (sin secretos ni rutas personales).
