# Generador vectorial de documentos PDF 1.4
# Aplica herencia: ConstructorPDF -> ReciboPDFDonante / InformePDFReceptor
from django.utils import timezone


# Paleta institucional HAMBRE CERO en RGB normalizado (0.0 a 1.0)
COLOR_PRIMARIO = (0.35, 0.41, 0.91)      # Azul índigo institucional
COLOR_PRIMARIO_SUAVE = (0.93, 0.95, 1.0) # Fondo índigo claro
COLOR_ACENTO = (0.54, 0.63, 1.0)         # Acento secundario
COLOR_TEXTO = (0.17, 0.19, 0.27)         # Texto principal oscuro
COLOR_GRIS = (0.42, 0.44, 0.52)          # Texto secundario
COLOR_BORDE = (0.86, 0.88, 0.93)         # Líneas y bordes suaves
COLOR_FONDO_FILA = (0.97, 0.98, 0.99)    # Fila alternada de tabla
COLOR_VERDE = (0.07, 0.65, 0.35)         # Aceptado / Éxito
COLOR_NARANJA = (0.90, 0.49, 0.13)       # Reservado
COLOR_ROJO = (0.85, 0.24, 0.28)          # Rechazado
COLOR_BLANCO = (1.0, 1.0, 1.0)


def _limpiar_texto_pdf(texto):
    """Convierte texto Unicode a WinAnsi (cp1252) y escapa paréntesis y diagonales para PDF."""
    s = str(texto or '').replace('\r', ' ').replace('\n', ' ')
    # Codifica a cp1252 para conservar acentos en español (á, é, í, ó, ú, ñ, ¡, ¿)
    s_win = s.encode('cp1252', errors='replace').decode('cp1252')
    return s_win.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')


def _recortar(texto, max_len):
    """Recorta textos largos añadiendo puntos suspensivos para evitar desbordes en tabla."""
    s = str(texto or '').strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 2].rstrip() + '..'


def _envolver_lineas(texto, max_chars):
    """Divide un párrafo en líneas que no excedan max_chars caracteres."""
    palabras = str(texto or '').split()
    if not palabras:
        return ['']
    lineas = []
    actual = palabras[0]
    for p in palabras[1:]:
        if len(actual) + 1 + len(p) <= max_chars:
            actual += ' ' + p
        else:
            lineas.append(actual)
            actual = p
    lineas.append(actual)
    return lineas


class ConstructorPDF:
    """
    Clase base para construir documentos PDF 1.4 multipágina en tamaño Carta (612 x 792 pt)
    con soporte de colores RGB, figuras vectoriales, tablas y acentos en español.
    """
    ANCHO = 612
    ALTO = 792
    MARGEN_X = 44

    def __init__(self):
        # Cada página es una lista de comandos PDF en texto
        self.paginas = []
        self.comandos = []
        self.y = 750
        self.nueva_pagina()

    def nueva_pagina(self):
        """Agrega una nueva hoja en blanco al documento."""
        self.comandos = []
        self.paginas.append(self.comandos)
        self.y = 750

    def rect(self, x, y, w, h, fill_rgb=None, stroke_rgb=None, line_w=0.8):
        """Dibuja un rectángulo con relleno y/o borde opcional."""
        ops = ['q']
        if fill_rgb:
            ops.append(f"{fill_rgb[0]:.3f} {fill_rgb[1]:.3f} {fill_rgb[2]:.3f} rg")
        if stroke_rgb:
            ops.append(f"{stroke_rgb[0]:.3f} {stroke_rgb[1]:.3f} {stroke_rgb[2]:.3f} RG")
            ops.append(f"{line_w:.2f} w")
        ops.append(f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re")
        if fill_rgb and stroke_rgb:
            ops.append('B')
        elif fill_rgb:
            ops.append('f')
        elif stroke_rgb:
            ops.append('S')
        ops.append('Q')
        self.comandos.append(' '.join(ops))

    def poligono(self, puntos, fill_rgb):
        """Dibuja un polígono relleno (útil para acentos geométricos en encabezado)."""
        if len(puntos) < 3:
            return
        ops = ['q', f"{fill_rgb[0]:.3f} {fill_rgb[1]:.3f} {fill_rgb[2]:.3f} rg"]
        ops.append(f"{puntos[0][0]:.2f} {puntos[0][1]:.2f} m")
        for px, py in puntos[1:]:
            ops.append(f"{px:.2f} {py:.2f} l")
        ops.append('h f Q')
        self.comandos.append(' '.join(ops))

    def linea(self, x1, y1, x2, y2, stroke_rgb=COLOR_BORDE, line_w=1.0):
        """Dibuja una línea recta entre dos puntos."""
        self.comandos.append(
            f"q {stroke_rgb[0]:.3f} {stroke_rgb[1]:.3f} {stroke_rgb[2]:.3f} RG "
            f"{line_w:.2f} w {x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S Q"
        )

    def texto(self, x, y, txt, font='F1', size=10, rgb=COLOR_TEXTO):
        """Escribe una línea de texto en la posición (x, y)."""
        seguro = _limpiar_texto_pdf(txt)
        self.comandos.append(
            f"q {rgb[0]:.3f} {rgb[1]:.3f} {rgb[2]:.3f} rg "
            f"BT /{font} {size:.1f} Tf {x:.2f} {y:.2f} Td ({seguro}) Tj ET Q"
        )

    def _ancho_aprox(self, txt, size, font='F1'):
        """Estima el ancho en puntos de un texto en Helvetica para centrado/alineación derecha."""
        factor = 0.53 if font == 'F2' else 0.50
        return len(str(txt or '')) * size * factor

    def texto_centrado(self, cx, y, txt, font='F1', size=10, rgb=COLOR_TEXTO):
        """Dibuja texto centrado horizontalmente respecto a cx."""
        x = cx - (self._ancho_aprox(txt, size, font) / 2.0)
        self.texto(x, y, txt, font=font, size=size, rgb=rgb)

    def texto_derecha(self, rx, y, txt, font='F1', size=10, rgb=COLOR_TEXTO):
        """Dibuja texto alineado a la derecha respecto a rx."""
        x = rx - self._ancho_aprox(txt, size, font)
        self.texto(x, y, txt, font=font, size=size, rgb=rgb)

    def parrafo(self, x, y, txt, max_chars=88, font='F1', size=9.5, leading=14, rgb=COLOR_TEXTO):
        """Dibuja un párrafo multi-línea y retorna la coordenada Y final."""
        for linea in _envolver_lineas(txt, max_chars):
            self.texto(x, y, linea, font=font, size=size, rgb=rgb)
            y -= leading
        return y

    def dibujar_pie_pagina(self, numero_pagina, total_paginas, etiqueta):
        """Coloca el pie institucional en la parte inferior de cada hoja."""
        self.linea(self.MARGEN_X, 46, self.ANCHO - self.MARGEN_X, 46, COLOR_BORDE, 0.7)
        self.texto(
            self.MARGEN_X,
            32,
            f"HAMBRE CERO · {etiqueta} · Documento generado electrónicamente",
            font='F1',
            size=7.8,
            rgb=COLOR_GRIS,
        )
        self.texto_derecha(
            self.ANCHO - self.MARGEN_X,
            32,
            f"Página {numero_pagina} de {total_paginas}",
            font='F1',
            size=7.8,
            rgb=COLOR_GRIS,
        )

    def construir_bytes(self):
        """Ensambla el archivo binario PDF 1.4 completo con fuentes WinAnsi y tabla xref."""
        # Objetos fijos: 1=Catalog, 2=Pages, 3=F1(Helvetica), 4=F2(Bold), 5=F3(Oblique)
        num_paginas = len(self.paginas)
        page_ids = []
        objetos = []

        # Reservamos 1..5
        for _ in range(5):
            objetos.append(b"")

        next_id = 6
        for comandos_pag in self.paginas:
            stream_txt = '\n'.join(comandos_pag)
            stream_bytes = stream_txt.encode('cp1252', errors='replace')
            content_id = next_id
            page_id = next_id + 1
            next_id += 2
            page_ids.append(page_id)

            objetos.append(
                f"{content_id} 0 obj\n<< /Length {len(stream_bytes)} >>\nstream\n".encode('ascii')
                + stream_bytes
                + b"\nendstream\nendobj\n"
            )
            objetos.append(
                (
                    f"{page_id} 0 obj\n"
                    f"<< /Type /Page /Parent 2 0 R "
                    f"/Resources << /Font << /F1 3 0 R /F2 4 0 R /F3 5 0 R >> >> "
                    f"/MediaBox [0 0 {self.ANCHO} {self.ALTO}] /Contents {content_id} 0 R >>\n"
                    f"endobj\n"
                ).encode('ascii')
            )

        kids_str = ' '.join(f"{pid} 0 R" for pid in page_ids)
        objetos[0] = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        objetos[1] = f"2 0 obj\n<< /Type /Pages /Kids [{kids_str}] /Count {num_paginas} >>\nendobj\n".encode('ascii')
        objetos[2] = b"3 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>\nendobj\n"
        objetos[3] = b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>\nendobj\n"
        objetos[4] = b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Oblique /Encoding /WinAnsiEncoding >>\nendobj\n"

        pdf = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
        offsets = []
        for obj in objetos:
            offsets.append(len(pdf))
            pdf += obj

        xref_offset = len(pdf)
        pdf += f"xref\n0 {len(objetos) + 1}\n0000000000 65535 f \n".encode('ascii')
        for off in offsets:
            pdf += f"{off:010d} 00000 n \n".encode('ascii')
        pdf += (
            f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF"
        ).encode('ascii')
        return pdf


def _etiqueta_periodo(periodo):
    """Traduce la clave de periodo a texto legible para el PDF."""
    mapa = {
        'dia': 'Últimas 24 horas (1 día)',
        'semana': 'Recientes (últimos 7 días)',
        'todas': 'Histórico completo (todas)',
    }
    return mapa.get(periodo, 'Histórico completo (todas)')


class ReciboPDFDonante(ConstructorPDF):
    """
    Plantilla formal 'Recibo de Donación' para el rol Donante.
    Inspirada en un comprobante institucional de recepción y agradecimiento.
    """

    def generar(self, usuario, donaciones, periodo='todas'):
        ahora = timezone.localtime(timezone.now())
        fecha_emision = ahora.strftime('%d/%m/%Y %H:%M')
        folio = f"HC-DON-{ahora.strftime('%Y%m%d')}-{usuario.pk:03d}"

        # Obtiene datos de perfil del donante de forma segura
        perfil = getattr(usuario, 'donante', usuario)
        razon_social = getattr(perfil, 'nombre_local', '') or usuario.username
        telefono = getattr(perfil, 'telefono', '') or 'No registrado'
        direccion = getattr(perfil, 'direccion', '') or 'No registrada'
        correo = usuario.email or 'No registrado'

        # Dibuja encabezado institucional con acentos geométricos en la esquina superior derecha
        self._dibujar_encabezado_donante()

        # Título principal centrado estilo "Recibo de Donación"
        self.texto_centrado(self.ANCHO / 2, 672, "Recibo de Donación", font='F2', size=20, rgb=COLOR_TEXTO)
        self.texto_centrado(
            self.ANCHO / 2,
            654,
            f"Folio: {folio}   |   Fecha de emisión: {fecha_emision}   |   Periodo: {_etiqueta_periodo(periodo)}",
            font='F1',
            size=8.5,
            rgb=COLOR_GRIS,
        )

        # Carta formal de agradecimiento y constancia de recepción
        y = 626
        self.texto(self.MARGEN_X, y, "¡Gracias por su generosidad!", font='F2', size=11, rgb=COLOR_PRIMARIO)
        y -= 18
        y = self.parrafo(
            self.MARGEN_X,
            y,
            "La aportación alimentaria que usted ha realizado marca una verdadera diferencia, contribuyendo a combatir el desperdicio de alimentos y apoyando a comedores comunitarios y familias en situación vulnerable.",
            max_chars=92,
            font='F1',
            size=9.5,
            leading=13.5,
            rgb=COLOR_TEXTO,
        )
        y -= 6
        y = self.parrafo(
            self.MARGEN_X,
            y,
            "Este recibo certifica que hemos recibido con gratitud sus donaciones registradas en el Sistema de Gestión de Recursos Alimentarios HAMBRE CERO. Conserve este comprobante como constancia oficial de sus aportaciones.",
            max_chars=92,
            font='F1',
            size=9.5,
            leading=13.5,
            rgb=COLOR_TEXTO,
        )

        # Caja de Información del Donante
        y -= 10
        caja_h = 66
        self.rect(self.MARGEN_X, y - caja_h, self.ANCHO - 2 * self.MARGEN_X, caja_h, fill_rgb=COLOR_FONDO_FILA, stroke_rgb=COLOR_BORDE)
        self.texto(self.MARGEN_X + 12, y - 16, "DATOS DEL DONANTE", font='F2', size=8.5, rgb=COLOR_PRIMARIO)
        self.texto(self.MARGEN_X + 12, y - 32, f"Nombre / Razón Social: {_recortar(razon_social, 36)}", font='F2', size=9, rgb=COLOR_TEXTO)
        self.texto(self.MARGEN_X + 290, y - 32, f"Teléfono: {_recortar(telefono, 24)}", font='F1', size=9, rgb=COLOR_TEXTO)
        self.texto(self.MARGEN_X + 12, y - 48, f"Dirección: {_recortar(direccion, 42)}", font='F1', size=9, rgb=COLOR_TEXTO)
        self.texto(self.MARGEN_X + 290, y - 48, f"Correo: {_recortar(correo, 28)}", font='F1', size=9, rgb=COLOR_TEXTO)
        y -= (caja_h + 14)

        # Métricas resumen del periodo
        total_reg = len(donaciones)
        peso_total = sum(float(d.peso_kg or 0) for d in donaciones)
        aceptadas = sum(1 for d in donaciones if d.estado in ('Aceptado', 'Entregada', 'Recibido'))
        ancho_kpi = (self.ANCHO - 2 * self.MARGEN_X - 20) / 3
        kpis = [
            ("DONACIONES EN PERIODO", str(total_reg)),
            ("PESO TOTAL APORTADO", f"{peso_total:,.1f} KG".replace('.0 KG', ' KG')),
            ("RECIBIDAS / ACEPTADAS", str(aceptadas)),
        ]
        for idx, (lbl, val) in enumerate(kpis):
            kx = self.MARGEN_X + idx * (ancho_kpi + 10)
            self.rect(kx, y - 44, ancho_kpi, 44, fill_rgb=COLOR_PRIMARIO_SUAVE, stroke_rgb=COLOR_BORDE)
            self.texto(kx + 10, y - 15, lbl, font='F2', size=7.2, rgb=COLOR_GRIS)
            self.texto(kx + 10, y - 34, val, font='F2', size=13, rgb=COLOR_PRIMARIO)
        y -= 62

        # Tabla detallada de donaciones recibidas
        self.texto(self.MARGEN_X, y, "DESGLOSE DE DONACIONES REGISTRADAS Y RECIBIDAS", font='F2', size=9.5, rgb=COLOR_TEXTO)
        y -= 10
        y = self._dibujar_cabecera_tabla_donante(y)

        if not donaciones:
            self.rect(self.MARGEN_X, y - 28, self.ANCHO - 2 * self.MARGEN_X, 28, fill_rgb=COLOR_FONDO_FILA, stroke_rgb=COLOR_BORDE)
            self.texto_centrado(
                self.ANCHO / 2,
                y - 18,
                "No se encontraron donaciones registradas en el periodo seleccionado.",
                font='F3',
                size=9,
                rgb=COLOR_GRIS,
            )
            y -= 36
        else:
            for idx, d in enumerate(donaciones):
                if y < 145:
                    self.nueva_pagina()
                    self._dibujar_encabezado_donante()
                    y = 682
                    y = self._dibujar_cabecera_tabla_donante(y)

                fila_h = 22
                fondo = COLOR_FONDO_FILA if idx % 2 == 1 else COLOR_BLANCO
                self.rect(self.MARGEN_X, y - fila_h, self.ANCHO - 2 * self.MARGEN_X, fila_h, fill_rgb=fondo, stroke_rgb=COLOR_BORDE, line_w=0.4)

                fecha_reg = timezone.localtime(d.fecha_registro).strftime('%d/%m/%Y') if d.fecha_registro else 'N/A'
                cad = (
                    d.fecha_caducidad.strftime('%d/%m/%Y')
                    if d.fecha_caducidad
                    else (d.alimento.fecha_caducidad.strftime('%d/%m/%Y') if d.alimento and d.alimento.fecha_caducidad else 'N/A')
                )
                alimento_txt = _recortar(d.alimento.nombre if d.alimento else 'Alimento', 26)
                cant_txt = _recortar(d.cantidad, 15)
                estado_color = COLOR_VERDE if d.estado in ('Aceptado', 'Entregada', 'Recibido') else (COLOR_ROJO if d.estado in ('Rechazado', 'Cancelada') else COLOR_NARANJA)

                self.texto(self.MARGEN_X + 8, y - 15, f"#{d.id:03d}", font='F2', size=8.5, rgb=COLOR_PRIMARIO)
                self.texto(self.MARGEN_X + 52, y - 15, fecha_reg, font='F1', size=8.5, rgb=COLOR_TEXTO)
                self.texto(self.MARGEN_X + 118, y - 15, alimento_txt, font='F2', size=8.5, rgb=COLOR_TEXTO)
                self.texto(self.MARGEN_X + 278, y - 15, cant_txt, font='F1', size=8.5, rgb=COLOR_TEXTO)
                self.texto(self.MARGEN_X + 372, y - 15, cad, font='F1', size=8.5, rgb=COLOR_TEXTO)
                self.texto(self.MARGEN_X + 446, y - 15, _recortar(d.estado, 12), font='F2', size=8.5, rgb=estado_color)
                y -= fila_h

        # Bloque de firma oficial HAMBRE CERO
        if y < 120:
            self.nueva_pagina()
            self._dibujar_encabezado_donante()
            y = 660

        y_firma = max(y - 42, 95)
        self.linea(self.ANCHO / 2 - 110, y_firma, self.ANCHO / 2 + 110, y_firma, COLOR_TEXTO, 0.9)
        self.texto_centrado(self.ANCHO / 2, y_firma - 14, "HAMBRE CERO", font='F2', size=10, rgb=COLOR_PRIMARIO)
        self.texto_centrado(
            self.ANCHO / 2,
            y_firma - 26,
            "Dirección de Acopio y Gestión de Recursos Alimentarios · Sello de Recepción Oficial",
            font='F3',
            size=8,
            rgb=COLOR_GRIS,
        )

        # Pie de página en todas las hojas
        total_pags = len(self.paginas)
        for i, comandos_pag in enumerate(self.paginas, start=1):
            self.comandos = comandos_pag
            self.dibujar_pie_pagina(i, total_pags, f"Recibo de Donación ({folio})")

        return self.construir_bytes()

    def _dibujar_encabezado_donante(self):
        """Dibuja el membrete superior estilo carta formal con acento geométrico derecho."""
        # Acentos diagonales en la esquina superior derecha (estilo 2da imagen en paleta Hambre Cero)
        self.poligono([(465, 792), (612, 792), (612, 700)], (0.86, 0.89, 1.0))
        self.poligono([(525, 792), (612, 792), (612, 735)], COLOR_ACENTO)

        # Insignia cuadrada "HC" + título de la organización
        self.rect(self.MARGEN_X, 720, 36, 36, fill_rgb=COLOR_PRIMARIO)
        self.texto_centrado(self.MARGEN_X + 18, 733, "HC", font='F2', size=14, rgb=COLOR_BLANCO)
        self.texto(self.MARGEN_X + 46, 742, "HAMBRE CERO", font='F2', size=15, rgb=COLOR_PRIMARIO)
        self.linea(self.MARGEN_X + 46, 734, 495, 734, COLOR_BORDE, 1.0)
        self.texto(
            self.MARGEN_X + 46,
            720,
            "Sistema de Gestión de Recursos Alimentarios · Av. Reforma 123, CDMX · soporte@hambrecero.org",
            font='F1',
            size=8,
            rgb=COLOR_GRIS,
        )

    def _dibujar_cabecera_tabla_donante(self, y):
        """Dibuja la fila de encabezados de la tabla del recibo de donante."""
        h = 22
        self.rect(self.MARGEN_X, y - h, self.ANCHO - 2 * self.MARGEN_X, h, fill_rgb=COLOR_PRIMARIO)
        self.texto(self.MARGEN_X + 8, y - 15, "FOLIO", font='F2', size=8, rgb=COLOR_BLANCO)
        self.texto(self.MARGEN_X + 52, y - 15, "FECHA", font='F2', size=8, rgb=COLOR_BLANCO)
        self.texto(self.MARGEN_X + 118, y - 15, "ALIMENTO", font='F2', size=8, rgb=COLOR_BLANCO)
        self.texto(self.MARGEN_X + 278, y - 15, "CANTIDAD", font='F2', size=8, rgb=COLOR_BLANCO)
        self.texto(self.MARGEN_X + 372, y - 15, "CADUCIDAD", font='F2', size=8, rgb=COLOR_BLANCO)
        self.texto(self.MARGEN_X + 446, y - 15, "ESTADO", font='F2', size=8, rgb=COLOR_BLANCO)
        return y - h


class InformePDFReceptor(ConstructorPDF):
    """
    Plantilla formal de 'Informe y Recibo de Gestión de Donaciones' para el rol Receptor.
    Muestra el trabajo realizado por la organización receptora, alimentos aceptados y entregados,
    fechas, lista de verificación y firmas oficiales con sello de HAMBRE CERO.
    """

    def generar(self, usuario, donaciones, periodo='todas'):
        ahora = timezone.localtime(timezone.now())
        fecha_emision = ahora.strftime('%d/%m/%Y %H:%M')
        folio = f"HC-REC-{ahora.strftime('%Y%m%d')}-{usuario.pk:03d}"

        # Datos del perfil receptor
        perfil = getattr(usuario, 'receptor', usuario)
        nombre_org = getattr(perfil, 'nombre_org', '') or usuario.username
        telefono = getattr(perfil, 'telefono', '') or 'No registrado'
        direccion = getattr(perfil, 'direccion', '') or 'No registrada'
        correo = usuario.email or 'No registrado'

        # Encabezado formal con doble franja superior (estilo 1ra imagen adaptado a Hambre Cero)
        self._dibujar_encabezado_receptor(folio, fecha_emision)

        # Sección 1: Información de la Organización Receptora
        y = 682
        self.texto(self.MARGEN_X, y, "1. INFORMACIÓN DE LA ORGANIZACIÓN RECEPTORA", font='F2', size=9.5, rgb=COLOR_PRIMARIO)
        y -= 6
        caja_h = 62
        self.rect(self.MARGEN_X, y - caja_h, self.ANCHO - 2 * self.MARGEN_X, caja_h, fill_rgb=COLOR_FONDO_FILA, stroke_rgb=COLOR_BORDE)
        self.texto(self.MARGEN_X + 12, y - 17, f"Organización / Asociación: {_recortar(nombre_org, 34)}", font='F2', size=9, rgb=COLOR_TEXTO)
        self.texto(self.MARGEN_X + 300, y - 17, f"Responsable: {_recortar(usuario.username, 24)}", font='F1', size=9, rgb=COLOR_TEXTO)
        self.texto(self.MARGEN_X + 12, y - 34, f"Dirección: {_recortar(direccion, 40)}", font='F1', size=9, rgb=COLOR_TEXTO)
        self.texto(self.MARGEN_X + 300, y - 34, f"Teléfono: {_recortar(telefono, 24)}", font='F1', size=9, rgb=COLOR_TEXTO)
        self.texto(self.MARGEN_X + 12, y - 51, f"Periodo del informe: {_etiqueta_periodo(periodo)}", font='F2', size=8.5, rgb=COLOR_PRIMARIO)
        self.texto(self.MARGEN_X + 300, y - 51, f"Correo: {_recortar(correo, 28)}", font='F1', size=8.5, rgb=COLOR_GRIS)
        y -= (caja_h + 16)

        # Sección 2: Resumen del Trabajo Realizado (KPIs)
        total_gest = len(donaciones)
        aceptadas_list = [d for d in donaciones if d.estado in ('Aceptado', 'Entregada')]
        reservadas = sum(1 for d in donaciones if d.estado in ('Reservado', 'Reservada'))
        rechazadas = sum(1 for d in donaciones if d.estado in ('Rechazado', 'Cancelada'))
        peso_aceptado = sum(float(d.peso_kg or 0) for d in aceptadas_list)

        self.texto(self.MARGEN_X, y, "2. RESUMEN DEL TRABAJO REALIZADO Y ENTREGAS A ASOCIACIONES", font='F2', size=9.5, rgb=COLOR_PRIMARIO)
        y -= 8
        ancho_kpi = (self.ANCHO - 2 * self.MARGEN_X - 24) / 4
        kpis = [
            ("TOTAL GESTIONADAS", str(total_gest), COLOR_PRIMARIO),
            ("ACEPTADAS / ENTREG.", str(len(aceptadas_list)), COLOR_VERDE),
            ("KG CANALIZADOS", f"{peso_aceptado:,.1f} KG".replace('.0 KG', ' KG'), COLOR_VERDE),
            ("RESERV. / RECHAZ.", f"{reservadas} / {rechazadas}", COLOR_NARANJA),
        ]
        for idx, (lbl, val, col) in enumerate(kpis):
            kx = self.MARGEN_X + idx * (ancho_kpi + 8)
            self.rect(kx, y - 44, ancho_kpi, 44, fill_rgb=COLOR_PRIMARIO_SUAVE, stroke_rgb=COLOR_BORDE)
            self.texto(kx + 8, y - 15, lbl, font='F2', size=6.8, rgb=COLOR_GRIS)
            self.texto(kx + 8, y - 34, val, font='F2', size=12, rgb=col)
        y -= 60

        # Sección 3: Desglose estructurado de donaciones gestionadas
        self.texto(self.MARGEN_X, y, "3. DETALLE DE ALIMENTOS ACEPTADOS, RESERVADOS Y GESTIONADOS", font='F2', size=9.5, rgb=COLOR_PRIMARIO)
        y -= 8
        y = self._dibujar_cabecera_tabla_receptor(y)

        if not donaciones:
            self.rect(self.MARGEN_X, y - 28, self.ANCHO - 2 * self.MARGEN_X, 28, fill_rgb=COLOR_FONDO_FILA, stroke_rgb=COLOR_BORDE)
            self.texto_centrado(
                self.ANCHO / 2,
                y - 18,
                "No se registran donaciones gestionadas por esta organización en el periodo seleccionado.",
                font='F3',
                size=8.8,
                rgb=COLOR_GRIS,
            )
            y -= 36
        else:
            for idx, d in enumerate(donaciones):
                if y < 190:
                    self.nueva_pagina()
                    self._dibujar_encabezado_receptor(folio, fecha_emision)
                    y = 682
                    y = self._dibujar_cabecera_tabla_receptor(y)

                fila_h = 22
                fondo = COLOR_FONDO_FILA if idx % 2 == 1 else COLOR_BLANCO
                self.rect(self.MARGEN_X, y - fila_h, self.ANCHO - 2 * self.MARGEN_X, fila_h, fill_rgb=fondo, stroke_rgb=COLOR_BORDE, line_w=0.4)

                fecha_ref = d.fecha_recepcion or d.fecha_registro
                fecha_txt = timezone.localtime(fecha_ref).strftime('%d/%m/%Y') if fecha_ref else 'N/A'
                origen = (
                    d.nombre_donante
                    or (d.donante.nombre_local if d.donante and d.donante.nombre_local else None)
                    or (d.usuario_donante.username if d.usuario_donante else 'Donante')
                )
                alimento_txt = _recortar(d.alimento.nombre if d.alimento else 'Alimento', 22)
                cant_txt = _recortar(d.cantidad, 13)
                peso_txt = f"{float(d.peso_kg or 0):g} kg"
                estado_color = COLOR_VERDE if d.estado in ('Aceptado', 'Entregada') else (COLOR_ROJO if d.estado in ('Rechazado', 'Cancelada') else COLOR_NARANJA)

                self.texto(self.MARGEN_X + 6, y - 15, f"#{d.id:03d}", font='F2', size=8.2, rgb=COLOR_PRIMARIO)
                self.texto(self.MARGEN_X + 44, y - 15, fecha_txt, font='F1', size=8.2, rgb=COLOR_TEXTO)
                self.texto(self.MARGEN_X + 102, y - 15, _recortar(origen, 17), font='F1', size=8.2, rgb=COLOR_TEXTO)
                self.texto(self.MARGEN_X + 202, y - 15, alimento_txt, font='F2', size=8.2, rgb=COLOR_TEXTO)
                self.texto(self.MARGEN_X + 332, y - 15, cant_txt, font='F1', size=8.2, rgb=COLOR_TEXTO)
                self.texto(self.MARGEN_X + 410, y - 15, peso_txt, font='F1', size=8.2, rgb=COLOR_TEXTO)
                self.texto(self.MARGEN_X + 458, y - 15, _recortar(d.estado, 11), font='F2', size=8.2, rgb=estado_color)
                y -= fila_h

        # Si queda poco espacio para lista de verificación + firmas, abre nueva hoja
        if y < 200:
            self.nueva_pagina()
            self._dibujar_encabezado_receptor(folio, fecha_emision)
            y = 675

        # Sección 4: Lista de verificación e información extra (inspirada en 1ra imagen)
        y -= 16
        self.texto(self.MARGEN_X, y, "4. VERIFICACIÓN DE RECEPCIÓN Y ENTREGA A ASOCIACIONES", font='F2', size=9.2, rgb=COLOR_PRIMARIO)
        y -= 14
        checks = [
            "[X] Control sanitario, condición física y verificación de fechas de caducidad realizadas.",
            "[X] Registro de movimientos de inventario y trazabilidad en la plataforma HAMBRE CERO.",
            "[X] Alimentos aceptados canalizados a comedores, albergues o asociaciones beneficiarias.",
            "[X] Evidencia fotográfica y comentarios de recepción respaldados en el historial privado.",
        ]
        for chk in checks:
            self.texto(self.MARGEN_X + 8, y, chk, font='F1', size=8.4, rgb=COLOR_TEXTO)
            y -= 13

        # Sección 5: Doble bloque de firmas (Receptor + HAMBRE CERO)
        y_firma = max(y - 38, 92)
        # Firma izquierda: Responsable Receptor
        self.linea(self.MARGEN_X + 10, y_firma, self.MARGEN_X + 225, y_firma, COLOR_TEXTO, 0.9)
        self.texto_centrado(self.MARGEN_X + 117, y_firma - 13, "FIRMA RESPONSABLE RECEPTOR", font='F2', size=8.5, rgb=COLOR_TEXTO)
        self.texto_centrado(self.MARGEN_X + 117, y_firma - 24, _recortar(nombre_org, 34), font='F1', size=8, rgb=COLOR_GRIS)
        self.texto_centrado(self.MARGEN_X + 117, y_firma - 35, "Vo. Bo. Coordinación de Entregas", font='F3', size=7.5, rgb=COLOR_GRIS)

        # Firma derecha: HAMBRE CERO
        rx_ini = self.ANCHO - self.MARGEN_X - 225
        rx_fin = self.ANCHO - self.MARGEN_X - 10
        rx_mid = (rx_ini + rx_fin) / 2
        self.linea(rx_ini, y_firma, rx_fin, y_firma, COLOR_PRIMARIO, 1.0)
        self.texto_centrado(rx_mid, y_firma - 13, "FIRMA OFICIAL — HAMBRE CERO", font='F2', size=8.5, rgb=COLOR_PRIMARIO)
        self.texto_centrado(rx_mid, y_firma - 24, "Dirección de Acopio y Distribución Alimentaria", font='F1', size=8, rgb=COLOR_GRIS)
        self.texto_centrado(rx_mid, y_firma - 35, "Vo. Bo. Auditoría y Trazabilidad", font='F3', size=7.5, rgb=COLOR_GRIS)

        # Pie de página en todas las hojas
        total_pags = len(self.paginas)
        for i, comandos_pag in enumerate(self.paginas, start=1):
            self.comandos = comandos_pag
            self.dibujar_pie_pagina(i, total_pags, f"Informe de Gestión Receptor ({folio})")

        return self.construir_bytes()

    def _dibujar_encabezado_receptor(self, folio, fecha_emision):
        """Dibuja encabezado formal con barras de énfasis superior e inferior."""
        self.rect(self.MARGEN_X, 756, 350, 3, fill_rgb=COLOR_PRIMARIO)
        self.texto(self.MARGEN_X, 738, "FORMATO E INFORME DE GESTIÓN", font='F2', size=14.5, rgb=COLOR_TEXTO)
        self.texto(self.MARGEN_X, 723, "Recibo de Donaciones Aceptadas y Entregadas — HAMBRE CERO", font='F2', size=9.2, rgb=COLOR_PRIMARIO)
        self.rect(self.MARGEN_X, 714, 350, 3, fill_rgb=COLOR_PRIMARIO)

        # Recuadro derecho de identificación institucional
        bx = 412
        bw = self.ANCHO - self.MARGEN_X - bx
        self.rect(bx, 712, bw, 48, fill_rgb=COLOR_PRIMARIO_SUAVE, stroke_rgb=COLOR_PRIMARIO, line_w=0.9)
        self.texto_centrado(bx + bw / 2, 745, "HAMBRE CERO", font='F2', size=11, rgb=COLOR_PRIMARIO)
        self.texto_centrado(bx + bw / 2, 731, folio, font='F2', size=7.8, rgb=COLOR_TEXTO)
        self.texto_centrado(bx + bw / 2, 719, f"Emitido: {fecha_emision}", font='F1', size=7.5, rgb=COLOR_GRIS)

    def _dibujar_cabecera_tabla_receptor(self, y):
        """Dibuja encabezados de la tabla de gestión del receptor."""
        h = 22
        self.rect(self.MARGEN_X, y - h, self.ANCHO - 2 * self.MARGEN_X, h, fill_rgb=COLOR_PRIMARIO)
        self.texto(self.MARGEN_X + 6, y - 15, "FOLIO", font='F2', size=7.8, rgb=COLOR_BLANCO)
        self.texto(self.MARGEN_X + 44, y - 15, "FECHA", font='F2', size=7.8, rgb=COLOR_BLANCO)
        self.texto(self.MARGEN_X + 102, y - 15, "DONANTE", font='F2', size=7.8, rgb=COLOR_BLANCO)
        self.texto(self.MARGEN_X + 202, y - 15, "ALIMENTO", font='F2', size=7.8, rgb=COLOR_BLANCO)
        self.texto(self.MARGEN_X + 332, y - 15, "CANTIDAD", font='F2', size=7.8, rgb=COLOR_BLANCO)
        self.texto(self.MARGEN_X + 410, y - 15, "PESO", font='F2', size=7.8, rgb=COLOR_BLANCO)
        self.texto(self.MARGEN_X + 458, y - 15, "ESTADO", font='F2', size=7.8, rgb=COLOR_BLANCO)
        return y - h


def generar_pdf_donante(usuario, donaciones, periodo='todas'):
    """Atajo para generar el Recibo de Donación en PDF para un Donante."""
    return ReciboPDFDonante().generar(usuario, list(donaciones), periodo=periodo)


def generar_pdf_receptor(usuario, donaciones, periodo='todas'):
    """Atajo para generar el Informe y Recibo de Gestión en PDF para un Receptor."""
    return InformePDFReceptor().generar(usuario, list(donaciones), periodo=periodo)
