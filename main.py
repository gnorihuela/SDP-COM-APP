import flet as ft
import pdfplumber
import os
import re
import calendar
import json
from datetime import datetime, date, timedelta

# --- PALETA EXACTA PC ---
BG_BASE = "#0F111A"
FG_MAIN = "#CFD8DC"
CYAN = "#00E5FF" 
ORANGE = "#FFEB3B" 
GREEN_UI = "#00E676"
BG_TRABAJO = "#8E1600"
BG_LIBRE = "#1B5E20"
BTN_BG = "#2A2F45" 

datos_empleados = {}
anio_base = 2026
mes_base = 1
lista_fechas_futuras = []

def main(page: ft.Page):
    global datos_empleados, anio_base, mes_base, lista_fechas_futuras

    page.title = "SDP-COM // Comando de Cuadrantes"
    page.bgcolor = BG_BASE
    page.theme_mode = "dark"
    page.padding = 20
    page.scroll = None 
    page.window_width = 700
    page.window_height = 950

    btn_style = ft.ButtonStyle(
        color=CYAN,
        bgcolor=BTN_BG,
        shape=ft.RoundedRectangleBorder(radius=4),
        overlay_color=ft.colors.with_opacity(0.2, CYAN), 
    )

    terminal_content = ft.Column(spacing=2, scroll="always", expand=True)

    def log(txt, col=FG_MAIN, b=False, bg=None):
        terminal_content.controls.append(
            ft.Text(txt, color=col, weight="bold" if b else "normal", 
                    size=17, font_family="monospace", bgcolor=bg)
        )
        page.update()

    def limpiar():
        terminal_content.controls.clear()
        page.update()

    # --- AUTOCOMPLETADO EN TIEMPO REAL EN TERMINAL ---
    def sugerir_atc_action(e):
        if not datos_empleados: return
        val = e.control.value.upper()
        if not val: 
            limpiar()
            return
            
        matches = [(k, d['nombre']) for k, d in datos_empleados.items() if k.startswith(val)]
        limpiar()
        log(f":: DIRECTORIO ATC [{val}] ::", CYAN, True)
        
        if matches:
            for k, nom in sorted(matches):
                log(f" > {k}  -  {nom}")
        else:
            log(" ❌ Sin coincidencias en el cuadrante.", "red")
        page.update()

    # --- LÓGICA DE NEGOCIO ---
    def obtener_comps_vertical(idx, t_ref, ic_propia):
        if t_ref in ["libre", "V", "B", "I"] or idx < 0: return ""
        f = "M" if "M" in t_ref else "T" if "T" in t_ref else "N" if "N" in t_ref else ""
        t = "1" if "1" in t_ref else "4" if "4" in t_ref else ""
        comps = [f"      - {d['nombre']} ({d['turnos'][idx]})" for ic, d in datos_empleados.items() 
                 if ic != ic_propia and idx < len(d['turnos']) and f in d['turnos'][idx] and t in d['turnos'][idx]]
        return "\n    Con:\n" + "\n".join(comps) if comps else ""

    # --- CORRECCIÓN 1: DETALLE SIN INVENTARSE EL DÍA DE HOY ---
    def detalle_inspeccion(dia_str, ic):
        if not ic: return
        limpiar()
        ic = ic.upper()
        if ic not in datos_empleados: return
        datos = datos_empleados[ic]
        
        hoy_dt = date.today()
        
        # Si dejas la casilla vacía, miramos si el mes/año cuadra. Si no, empezamos en el día 1.
        if not dia_str or not str(dia_str).isdigit():
            if hoy_dt.month == mes_base and hoy_dt.year == anio_base:
                dia_ini = hoy_dt.day
            else:
                dia_ini = 1
        else:
            dia_ini = int(dia_str)

        log(f"{datos['nombre']}", CYAN, True)

        semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        for i in range(5):
            dia_actual = dia_ini + i
            if dia_actual > len(datos["turnos"]): break
            idx = dia_actual - 1
            turno = datos["turnos"][idx]
            
            # Comparación exacta con el calendario real
            try:
                f_dt = date(anio_base, mes_base, dia_actual)
                nom_dia = semana[f_dt.weekday()]
                
                if f_dt == hoy_dt:
                    cabecera = f"[ Hoy - {nom_dia} {dia_actual} ]"
                elif f_dt == hoy_dt + timedelta(days=1):
                    cabecera = f"[ Mañana - {nom_dia} {dia_actual} ]"
                else:
                    cabecera = f"[ DÍA {dia_actual} - {nom_dia} ]"
            except: 
                cabecera = f"[ DÍA {dia_actual} - --- ]"

            log(f"\n{cabecera}", ORANGE, True)
            log(f"  TURNO: {turno}")
            comps = obtener_comps_vertical(idx, turno, ic)
            if comps: log(comps, CYAN)
        page.update()

    def ver_calendario_btn(e):
        limpiar()
        ic = in_inic.value.upper()
        if not ic or ic not in datos_empleados: return
        log(f":: CALENDARIO :: {datos_empleados[ic]['nombre']}", CYAN, True)
        
        terminal_content.controls.append(ft.Container(height=25)) 
        
        cal = calendar.monthcalendar(anio_base, mes_base)
        for week in cal:
            fila = ft.Row(spacing=4, alignment="center")
            for d in week:
                if d == 0: fila.controls.append(ft.Container(width=40))
                else:
                    t_val = datos_empleados[ic]["turnos"][d-1]
                    bg = ORANGE if t_val == "I" else (BG_LIBRE if t_val in ["libre", "V", "B"] else BG_TRABAJO)
                    fila.controls.append(ft.Container(
                        content=ft.Text(str(d), size=12, weight="bold", color="black" if t_val == "I" else "white"),
                        bgcolor=bg, width=40, height=40, border_radius=4, alignment=ft.alignment.center,
                        on_click=lambda e, day=d: detalle_inspeccion(str(day), ic)
                    ))
            terminal_content.controls.append(fila)

        turnos = datos_empleados[ic]["turnos"]
        libres = turnos.count("libre") + turnos.count("V") + turnos.count("B")
        imaginarias = turnos.count("I")
        trabajo = len(turnos) - libres - imaginarias

        terminal_content.controls.append(ft.Container(height=15)) 
        terminal_content.controls.append(
            ft.Row([
                ft.Container(content=ft.Text(f" TRABAJO: {trabajo} ", color="white", weight="bold"), bgcolor=BG_TRABAJO, padding=5, border_radius=3),
                ft.Container(content=ft.Text(f" IMAGINARIA: {imaginarias} ", color="black", weight="bold"), bgcolor=ORANGE, padding=5, border_radius=3),
                ft.Container(content=ft.Text(f" LIBRE: {libres} ", color="white", weight="bold"), bgcolor=BG_LIBRE, padding=5, border_radius=3),
            ], alignment="center", spacing=10)
        )
        page.update()

    # --- CORRECCIÓN 2: SIMULACIÓN 5-3 CON ANCLAJE INVERSO ---
    def simular_53_action(e):
        ic = in_inic.value.upper()
        if not ic or ic not in datos_empleados or not cb_sim.value: return
        limpiar()
        
        target_idx = int(cb_sim.value)
        target_y, target_m = lista_fechas_futuras[target_idx]
        turnos = datos_empleados[ic]["turnos"]
        
        anchor_date, anchor_state = None, None
        
        # Iteramos HACA ATRÁS para encontrar la ÚLTIMA rotación del mes (la más reciente)
        for i in range(len(turnos)-2, -1, -1):
            t_curr = turnos[i]
            t_next = turnos[i+1]
            
            es_libre_curr = t_curr in ["libre", "V", "B"]
            es_libre_next = t_next in ["libre", "V", "B"]
            
            # Pasamos de trabajar a descansar
            if not es_libre_curr and es_libre_next:
                anchor_date = date(anio_base, mes_base, i+2) # i+2 es el índice ajustado a formato fecha real
                anchor_state = 5 # Estado 5 significa "Día 1 de Libre"
                break
            # Pasamos de descansar a trabajar
            elif es_libre_curr and not es_libre_next:
                anchor_date = date(anio_base, mes_base, i+2)
                anchor_state = 0 # Estado 0 significa "Día 1 de Trabajo"
                break
        
        if not anchor_date: 
            log("ERROR: No se ha podido detectar un patrón de turnos para anclar.", "red")
            return
        
        meses_n = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        log(f":: PROYECCIÓN 5-3 :: {meses_n[target_m-1]} {target_y}", CYAN, True)
        
        terminal_content.controls.append(ft.Container(height=25)) 
        
        delta = date(target_y, target_m, 1) - anchor_date
        st_1st = (anchor_state + delta.days) % 8
        cal = calendar.monthcalendar(target_y, target_m)
        
        for week in cal:
            fila = ft.Row(spacing=4, alignment="center")
            for d in week:
                if d == 0:
                    fila.controls.append(ft.Container(width=40))
                else:
                    st = (st_1st + d - 1) % 8
                    is_libre = st >= 5
                    fila.controls.append(
                        ft.Container(
                            content=ft.Text(str(d), size=12, weight="bold", color="white"),
                            bgcolor=BG_LIBRE if is_libre else BG_TRABAJO,
                            width=40, height=40, border_radius=4, alignment=ft.alignment.center 
                        )
                    )
            terminal_content.controls.append(fila)
        page.update()

    def match_atc_action(e):
        ic1 = in_match_1.value.upper() if in_match_1.value else ""
        ic2 = in_match_2.value.upper() if in_match_2.value else ""
        
        limpiar()
        
        if not ic1 and not ic2:
            if not datos_empleados:
                log("ERROR: No hay cuadrante cargado.", "red")
                return
                
            log(":: TOP 5 PAREJAS DEL MES ::", CYAN, True)
            log("") 
            
            parejas = []
            atcs = list(datos_empleados.items())
            
            for i in range(len(atcs)):
                ic_A, d_A = atcs[i]
                t_A = d_A["turnos"]
                for j in range(i + 1, len(atcs)):
                    ic_B, d_B = atcs[j]
                    t_B = d_B["turnos"]
                    
                    coincidencias = 0
                    for idx in range(min(len(t_A), len(t_B))):
                        t1, t2 = t_A[idx], t_B[idx]
                        if t1 in ["libre", "V", "B", "I"] or t2 in ["libre", "V", "B", "I"]: continue
                        
                        f1 = "M" if "M" in t1 else "T" if "T" in t1 else "N" if "N" in t1 else ""
                        tt1 = "1" if "1" in t1 else "4" if "4" in t1 else ""
                        f2 = "M" if "M" in t2 else "T" if "T" in t2 else "N" if "N" in t2 else ""
                        tt2 = "1" if "1" in t2 else "4" if "4" in t2 else ""
                        
                        if f1 and f1 == f2 and tt1 and tt1 == tt2:
                            coincidencias += 1
                            
                    if coincidencias > 0:
                        parejas.append((coincidencias, ic_A, d_A['nombre'], ic_B, d_B['nombre']))
                        
            parejas.sort(key=lambda x: x[0], reverse=True)
            
            if not parejas:
                log("No hay turnos compartidos este mes.", FG_MAIN)
            else:
                for idx, (c, ic_A, nom_A, ic_B, nom_B) in enumerate(parejas[:5]):
                    log(f" {idx+1}. {ic_A} & {ic_B} -> {c} turnos", ORANGE, True)
                    log(f"    {nom_A} / {nom_B}\n", FG_MAIN)
            page.update()
            return

        if bool(ic1) != bool(ic2):
            ic_target = ic1 if ic1 else ic2
            if ic_target not in datos_empleados:
                log("ERROR: El ATC no existe en el cuadrante.", "red")
                return
            
            nom_target = datos_empleados[ic_target]['nombre']
            log(f":: TOP 5 RANKING DE COINCIDENCIAS ::", CYAN, True)
            log(f"ATC: {nom_target}\n")
            
            turnos1 = datos_empleados[ic_target]["turnos"]
            rank = []
            
            for ic_other, d2 in datos_empleados.items():
                if ic_target == ic_other: continue
                coincidencias = 0
                turnos2 = d2["turnos"]
                for idx in range(min(len(turnos1), len(turnos2))):
                    t1, t2 = turnos1[idx], turnos2[idx]
                    if t1 in ["libre", "V", "B", "I"] or t2 in ["libre", "V", "B", "I"]: continue
                    
                    f1 = "M" if "M" in t1 else "T" if "T" in t1 else "N" if "N" in t1 else ""
                    tt1 = "1" if "1" in t1 else "4" if "4" in t1 else ""
                    f2 = "M" if "M" in t2 else "T" if "T" in t2 else "N" if "N" in t2 else ""
                    tt2 = "1" if "1" in t2 else "4" if "4" in t2 else ""
                    
                    if f1 and f1 == f2 and tt1 and tt1 == tt2:
                        coincidencias += 1
                if coincidencias > 0:
                    rank.append((coincidencias, ic_other, d2['nombre']))
            
            rank.sort(key=lambda x: x[0], reverse=True)
            
            if not rank:
                log("No compartes turnos con nadie en tu franja y terminal.", FG_MAIN)
            else:
                for idx, (c, ic_o, nom) in enumerate(rank[:5]):
                    log(f" {idx+1}. {nom} ({ic_o}) -> {c} turnos", ORANGE, True)
            page.update()
            return

        if ic1 not in datos_empleados or ic2 not in datos_empleados:
            log("ERROR: Uno o ambos ATCs no existen en el cuadrante.", "red")
            return
            
        nom1 = datos_empleados[ic1]['nombre']
        nom2 = datos_empleados[ic2]['nombre']
        
        turnos1 = datos_empleados[ic1]["turnos"]
        turnos2 = datos_empleados[ic2]["turnos"]
        semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        
        lista_coincidencias = []
        for idx in range(min(len(turnos1), len(turnos2))):
            t1, t2 = turnos1[idx], turnos2[idx]
            if t1 in ["libre", "V", "B", "I"] or t2 in ["libre", "V", "B", "I"]: continue
            
            f1 = "M" if "M" in t1 else "T" if "T" in t1 else "N" if "N" in t1 else ""
            tt1 = "1" if "1" in t1 else "4" if "4" in t1 else ""
            f2 = "M" if "M" in t2 else "T" if "T" in t2 else "N" if "N" in t2 else ""
            tt2 = "1" if "1" in t2 else "4" if "4" in t2 else ""
            
            if f1 and f1 == f2 and tt1 and tt1 == tt2:
                dia_actual = idx + 1
                try:
                    f_dt = date(anio_base, mes_base, dia_actual)
                    nom_dia = semana[f_dt.weekday()]
                except:
                    nom_dia = "---"
                lista_coincidencias.append((dia_actual, nom_dia, t1, t2))
                
        log(f":: MATCH DE TURNOS ::", CYAN, True)
        log(f"{nom1} & {nom2}")
        
        if not lista_coincidencias:
            log("\nNo comparten ningún turno en la misma franja y terminal.", FG_MAIN)
        else:
            log(f"TOTAL DÍAS COMPARTIDOS: {len(lista_coincidencias)}\n", GREEN_UI, True)
            for dia_actual, nom_dia, t1, t2 in lista_coincidencias:
                log(f"[ DÍA {dia_actual} - {nom_dia} ]", ORANGE, True)
                log(f"  > {ic1}: {t1}")
                log(f"  > {ic2}: {t2}")

        page.update()

    def scan_torre_action(e):
        limpiar()
        dia_s, t_sel = in_dia_t.value, cb_torre.value
        if not datos_empleados or not dia_s.isdigit(): return
        idx = int(dia_s) - 1
        semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        try:
            f_dt = date(anio_base, mes_base, int(dia_s))
            nom_dia = semana[f_dt.weekday()]
        except: nom_dia = ""
        log(f":: ESTADO SECTOR {t_sel} :: DÍA {dia_s} - {nom_dia}", CYAN, True)
        log("") 
        activos, imaginarias = [], []
        for d in datos_empleados.values():
            if idx >= len(d["turnos"]): continue
            t = d["turnos"][idx]
            if t == "I": 
                imaginarias.append(f"> {d['nombre']}: {t}")
            elif t not in ["libre", "V", "B"] and ((t_sel == "T2" and "1" in t) or (t_sel == "T4" and "4" in t)):
                activos.append((t, f"> {d['nombre']}: {t}"))
        activos.sort(key=lambda x: x[0])
        for _, it in activos: log(it)
        if imaginarias:
            log(f"\n[ IMAGINARIAS ]", ORANGE, True)
            for it in sorted(imaginarias): log(it)
        page.update()

    def actualizar_opciones_simulador():
        opc = []
        meses_n = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        for i, (y, m) in enumerate(lista_fechas_futuras):
            opc.append(ft.dropdown.Option(str(i), f"{meses_n[m-1]} {y}"))
        cb_sim.options = opc
        cb_sim.update()

    def procesar_pdf(e):
        global datos_empleados, anio_base, mes_base, lista_fechas_futuras
        if not e.files: return
        limpiar()
        log("> ESTABLECIENDO DATALINK...", CYAN)
        try:
            ruta = e.files[0].path
            nombre_arc = os.path.basename(ruta)
            match = re.match(r'^(\d{2})(\d{2})_SDP', nombre_arc)
            if match: 
                anio_base = 2000 + int(match.group(1))
                mes_base = int(match.group(2))
            
            dias_del_mes = calendar.monthrange(anio_base, mes_base)[1]
            
            with pdfplumber.open(ruta) as pdf:
                tabla = pdf.pages[0].extract_tables()[0]
                temp = {}
                for fila in tabla:
                    if len(fila) >= (dias_del_mes + 3) and fila[2]:
                        nombre_op = str(fila[2]).replace('\n', ' ').strip()
                        
                        ic = ""
                        for val in reversed(fila[dias_del_mes + 3:]):
                            if val:
                                val_str = str(val).replace('\n', '').strip()
                                if val_str.isalpha() and 2 <= len(val_str) <= 4:
                                    ic = val_str
                                    break
                        
                        if not ic:
                            continue
                            
                        trs = [str(c).replace('\n', ' ').strip() if c and str(c).strip() != "" else "libre" for c in fila[3 : 3 + dias_del_mes]]
                        temp[ic] = {"nombre": nombre_op, "turnos": trs}
                        
                if not temp:
                    log("ERROR: La tabla está vacía. Comprueba el formato del PDF.", "red")
                    return
                    
                datos_empleados = temp
                
                lista_f = []
                m, y = mes_base, anio_base
                for i in range(12):
                    m += 1
                    if m > 12: m=1; y+=1
                    lista_f.append((y, m))
                lista_fechas_futuras = lista_f
                
                page.client_storage.set("datos_pdf", json.dumps(datos_empleados))
                page.client_storage.set("metadata_pdf", json.dumps({
                    "anio": anio_base, 
                    "mes": mes_base, 
                    "futuras": lista_fechas_futuras
                }))
                
                actualizar_opciones_simulador()
                log(f"> DATALINK OK Y GUARDADO: {len(datos_empleados)} ATCs", GREEN_UI)
        except Exception as ex: 
            log(f"ERROR: {ex}", "red")

    def section_frame(title, content, head_color, bg_inner=None, is_terminal=False):
        if is_terminal:
            return ft.Column([
                ft.Stack([
                    ft.Container(border=ft.border.all(1, "#333333"), height=10, margin=ft.margin.only(top=10), width=float("inf")),
                    ft.Container(content=ft.Text(f" [ {title} ] ", color=head_color, size=12, weight="bold"), bgcolor=BG_BASE, margin=ft.margin.only(left=15), padding=ft.padding.symmetric(horizontal=5))
                ]),
                ft.Container(content=content, bgcolor=bg_inner, border=ft.border.all(1, "#333333"), padding=15, width=float("inf"), expand=True)
            ], spacing=0, expand=True)
        else:
            return ft.Stack([
                ft.Container(
                    content=ft.Container(content=content, padding=ft.padding.only(top=15)),
                    border=ft.border.all(1, "#333333"),
                    padding=15,
                    margin=ft.margin.only(top=10),
                    width=float("inf")
                ),
                ft.Container(
                    content=ft.Text(f" [ {title} ] ", color=head_color, size=12, weight="bold"),
                    bgcolor=BG_BASE,
                    margin=ft.margin.only(left=15),
                    padding=ft.padding.symmetric(horizontal=5)
                )
            ])

    picker = ft.FilePicker(on_result=procesar_pdf)
    page.overlay.append(picker)

    in_dia_t = ft.TextField(label="DÍA", width=105, height=48, color="white", border_color="#555555", text_align="center")
    cb_torre = ft.Dropdown(options=[ft.dropdown.Option("T2"), ft.dropdown.Option("T4")], value="T2", width=105, height=48, color=CYAN, bgcolor=BTN_BG, border_color="#555555", content_padding=ft.padding.only(left=10, bottom=12))
    
    in_inic = ft.TextField(label="ID ATC", width=105, height=48, color="white", border_color="#555555", text_align="center", capitalization=ft.TextCapitalization.CHARACTERS, on_change=sugerir_atc_action)
    in_dia_op = ft.TextField(label="DÍA", width=105, height=48, color="white", border_color="#555555", text_align="center")
    
    cb_sim = ft.Dropdown(label="TARGET", width=220, height=48, color=CYAN, bgcolor=BTN_BG, border_color="#555555", content_padding=ft.padding.only(left=10, bottom=12))

    in_match_1 = ft.TextField(label="ID ATC", width=95, height=48, color="white", border_color="#555555", text_align="center", capitalization=ft.TextCapitalization.CHARACTERS, on_change=sugerir_atc_action)
    in_match_2 = ft.TextField(label="ID ATC", width=95, height=48, color="white", border_color="#555555", text_align="center", capitalization=ft.TextCapitalization.CHARACTERS, on_change=sugerir_atc_action)
    signo_mas = ft.Container(content=ft.Text("+", weight="bold", color=FG_MAIN, text_align="center"), width=10, alignment=ft.alignment.center)

    def cargar_memoria():
        global datos_empleados, anio_base, mes_base, lista_fechas_futuras
        if page.client_storage.contains_key("datos_pdf"):
            try:
                datos_raw = page.client_storage.get("datos_pdf")
                meta_raw = page.client_storage.get("metadata_pdf")
                
                if datos_raw and meta_raw:
                    datos_empleados = json.loads(datos_raw)
                    meta = json.loads(meta_raw)
                    anio_base = meta["anio"]
                    mes_base = meta["mes"]
                    lista_fechas_futuras = meta["futuras"]
                    
                    actualizar_opciones_simulador()
                    log(f"> DATALINK RESTAURADO ({len(datos_empleados)} ATCs)", GREEN_UI, True)
                    return
            except Exception:
                page.client_storage.remove("datos_pdf")
                page.client_storage.remove("metadata_pdf")
        
        log("> ESPERANDO CARGA DE PDF BASE...", FG_MAIN)

    cargar_memoria()

    page.add(
        ft.Column([
            section_frame("01 - DATALINK", ft.ElevatedButton("CARGAR PDF BASE", on_click=lambda _: picker.pick_files(), width=600, style=btn_style), FG_MAIN),
            
            section_frame("02 - ESCÁNER SECTOR", ft.Row([
                in_dia_t, 
                cb_torre, 
                ft.ElevatedButton("SCAN", on_click=scan_torre_action, width=130, style=btn_style)
            ], spacing=10), FG_MAIN),
            
            section_frame("03 - ID ATC", ft.Column([
                ft.Row([
                    in_inic, 
                    in_dia_op
                ], spacing=10),
                ft.Row([
                    ft.ElevatedButton("DETALLE", on_click=lambda _: detalle_inspeccion(in_dia_op.value, in_inic.value), expand=True, height=40, style=btn_style),
                    ft.ElevatedButton("CALENDARIO", on_click=ver_calendario_btn, expand=True, height=40, style=btn_style)
                ], spacing=10)
            ], spacing=10), FG_MAIN),
            
            section_frame("04 - SIMULACIÓN", ft.Column([
                ft.Row([
                    cb_sim, 
                    ft.ElevatedButton("EJECUTAR", on_click=simular_53_action, width=130, style=btn_style)
                ], spacing=10),
                ft.Row([
                    in_match_1,
                    signo_mas,
                    in_match_2,
                    ft.ElevatedButton("MATCH", on_click=match_atc_action, width=130, style=btn_style)
                ], spacing=10)
            ], spacing=10), FG_MAIN),
            
            section_frame("TERMINAL DE SALIDA", terminal_content, FG_MAIN, bg_inner=BTN_BG, is_terminal=True)
        ], spacing=15, expand=True)
    )

ft.app(target=main)
