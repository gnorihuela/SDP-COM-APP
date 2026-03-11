import flet as ft
import pdfplumber
import os
import re
import calendar
import json
from datetime import datetime, date

# Paleta de colores SDP-COM
BG_BASE = "#0F111A"
BG_PANEL = "#1E2233"
CYAN = "#00E5FF"
ORANGE = "#FFAB00"
GREEN_UI = "#00E676"
BG_TRABAJO = "#8E1600"
BG_LIBRE = "#1B5E20"
BG_IMAGINARIA = "#FFD54F"

class SistemaSDP:
    def __init__(self):
        self.datos_empleados = {}
        self.anio_base = 2026
        self.mes_base = 1

    def procesar_pdf(self, ruta):
        try:
            with pdfplumber.open(ruta) as pdf:
                nombre_archivo = os.path.basename(ruta)
                match = re.match(r'^(\d{2})(\d{2})_SDP', nombre_archivo)
                if match:
                    self.anio_base = 2000 + int(match.group(1))
                    self.mes_base = int(match.group(2))
                
                tabla = pdf.pages[0].extract_tables()[0]
                temp_datos = {}
                for fila in tabla:
                    if len(fila) >= 34:
                        nombre_raw = str(fila[2]).upper()
                        if not any(x in nombre_raw for x in ["FECHA", "NOMBRE", "DIA", "DÍA"]):
                            nombre = str(fila[2]).replace('\n', ' ').strip()
                            inic = str(fila[34] if len(fila)>34 else fila[-1]).strip()
                            turnos = [str(c).strip() if c else "libre" for c in fila[3:34]]
                            while len(turnos) < 31: turnos.append("libre")
                            temp_datos[inic] = {"nombre": nombre, "turnos": turnos}
                self.datos_empleados = temp_datos
            return True
        except: return False

def main(page: ft.Page):
    page.title = "SDP-COM Mobile"
    page.bgcolor = BG_BASE
    page.scroll = ft.ScrollMode.ADAPTIVE
    page.padding = 20
    
    sistema = SistemaSDP()
    res_area = ft.Column(spacing=10)
    txt_log = ft.Text("> ESPERANDO DATALINK...", color=CYAN, size=12)

    # --- MEMORIA: Carga de datos guardados ---
    def cargar_memoria():
        if page.client_storage.contains_key("datos_sdp"):
            datos_guardados = json.loads(page.client_storage.get("datos_sdp"))
            sistema.datos_empleados = datos_guardados["empleados"]
            sistema.anio_base = datos_guardados["anio"]
            sistema.mes_base = datos_guardados["mes"]
            txt_log.value = f"> SISTEMA ONLINE (CUADRANTE: {sistema.mes_base}/{sistema.anio_base})"
            txt_log.color = GREEN_UI
            page.update()

    # --- MEMORIA: Guardar datos ---
    def guardar_en_memoria():
        payload = {
            "empleados": sistema.datos_empleados,
            "anio": sistema.anio_base,
            "mes": sistema.mes_base
        }
        page.client_storage.set("datos_sdp", json.dumps(payload))

    # --- Funciones Táctiles ---
    def mostrar_detalle(e, iniciales, dia_inicio):
        res_area.controls.clear()
        if iniciales not in sistema.datos_empleados: return
        data = sistema.datos_empleados[iniciales]
        res_area.controls.append(ft.Text(f"OPERADOR: {data['nombre']}", color=CYAN, weight="bold", size=16))
        
        dias_sem = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        for i in range(5):
            d = dia_inicio + i
            if d > 31: break
            turno = data['turnos'][d-1]
            try: nom_dia = dias_sem[date(sistema.anio_base, sistema.mes_base, d).weekday()]
            except: nom_dia = ""
            
            res_area.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Text(f"DÍA {d} - {nom_dia}", color=ORANGE, weight="bold"),
                        ft.Text(f"ASIGNACIÓN: {turno}", color="white"),
                    ]),
                    padding=10, bgcolor=BG_PANEL, border_radius=10
                )
            )
        page.update()

    def ver_calendario_tactil(iniciales):
        res_area.controls.clear()
        if iniciales not in sistema.datos_empleados:
            res_area.controls.append(ft.Text("ERROR: CARGUE PDF O REVISE INICIALES", color="red"))
            page.update()
            return
        data = sistema.datos_empleados[iniciales]
        
        grid = ft.GridView(runs_count=7, max_extent=50, spacing=5, run_spacing=5)
        cal = calendar.monthcalendar(sistema.anio_base, sistema.mes_base)
        
        for week in cal:
            for day in week:
                if day == 0:
                    grid.controls.append(ft.Container())
                else:
                    turno = data['turnos'][day-1]
                    color = BG_LIBRE if turno in ["libre", "V", "B"] else BG_IMAGINARIA if turno == "I" else BG_TRABAJO
                    grid.controls.append(
                        ft.Container(
                            content=ft.Text(str(day), weight="bold", color="black" if turno=="I" else "white"),
                            bgcolor=color,
                            alignment=ft.alignment.center,
                            border_radius=5,
                            on_click=lambda e, d=day: mostrar_detalle(e, iniciales, d)
                        )
                    )
        res_area.controls.append(ft.Text(f"CUADRANTE: {data['nombre']}", color=GREEN_UI, size=14))
        res_area.controls.append(ft.Container(content=grid, height=300))
        page.update()

    # --- Interfaz Principal ---
    input_inic = ft.TextField(label="Iniciales Operador", autocapitalize=ft.TextCapitalization.CHARACTERS, border_color=CYAN)
    
    def on_file_result(e: ft.FilePickerResultEvent):
        if e.files:
            if sistema.procesar_pdf(e.files[0].path):
                guardar_en_memoria() # Guardamos para la próxima vez
                txt_log.value = f"> UPLINK EXITOSO: {sistema.mes_base}/{sistema.anio_base}"
                txt_log.color = GREEN_UI
            page.update()

    file_picker = ft.FilePicker(on_result=on_file_result)
    page.overlay.append(file_picker)

    page.add(
        ft.Text("SDP-COM COMMAND CENTER", size=22, color=CYAN, weight="bold"),
        ft.ElevatedButton("CARGAR NUEVO PDF", icon=ft.icons.UPLOAD_FILE, on_click=lambda _: file_picker.pick_files()),
        txt_log,
        ft.Container(height=10),
        input_inic,
        ft.Row([
            ft.ElevatedButton("VER CALENDARIO", icon=ft.icons.CALENDAR_MONTH, 
                              on_click=lambda _: ver_calendario_tactil(input_inic.value.upper()), expand=True),
        ]),
        ft.Divider(color="#333333"),
        res_area
    )

    # Ejecutar carga de memoria al abrir
    cargar_memoria()

ft.app(target=main)