def main(page: ft.Page):
    # --- BLOQUE DE DIAGNÓSTICO ---
    try:
        import pdfplumber
        import json
    except ImportError as e:
        page.add(ft.Text(f"ERROR DE LIBRERÍA: Falta {e.name}. Revisa requirements.txt", color="red", size=20))
        page.update()
        return
    except Exception as e:
        page.add(ft.Text(f"ERROR CRÍTICO AL INICIAR: {str(e)}", color="orange", size=20))
        page.update()
        return

    # Si pasa el diagnóstico, sigue tu código normal...
    global datos_empleados, anio_base, mes_base, lista_fechas_futuras
    page.title = "SDP-COM // Comando de Cuadrantes"
    # ... resto de tu código ...
