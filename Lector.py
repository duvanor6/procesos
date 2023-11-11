from flask import Flask, request, jsonify
import mysql.connector
import psutil

app = Flask(__name__)

db = mysql.connector.connect(
    host="localhost",
    user="duban",
    password="Duvan1997*",
    database="procesos"
)
cursor = db.cursor()

def obtener_procesos(orden, cantidad):
    procesos = []
    
    if orden == 'cpu':
        procesos = sorted(psutil.process_iter(attrs=['pid', 'name', 'username', 'cmdline', 'status', 'cpu_percent']),
                          key=lambda x: x.info['cpu_percent'], reverse=True)
    elif orden == 'ram':
        procesos = sorted(psutil.process_iter(attrs=['pid', 'name', 'username', 'cmdline', 'status', 'memory_percent']),
                          key=lambda x: x.info['memory_percent'], reverse=True)
    else:
        return "Orden no válida. Debe ser 'cpu' o 'ram'."

    procesos_filtrados = []
    nombres_procesos = set()
    for proceso in procesos:
        nombre = proceso.info['name']
        if nombre not in nombres_procesos:
            pid = proceso.info['pid']
            usuario = proceso.info['username']
            descripcion =  obtener_informacion_proceso(proceso.info['pid'])
            prioridad = 0 if usuario == "SOAIN\\duortega" else 1
            procesos_filtrados.append({'pid': pid, 'nombre': nombre, 'usuario': usuario, 'descripcion': descripcion, 'prioridad': prioridad})
            nombres_procesos.add(nombre)

        if len(procesos_filtrados) >= cantidad:
            break

    return procesos_filtrados

def obtener_informacion_proceso(pid):
    try:
        proceso = psutil.Process(pid)
        res = " "+str(pid)+" "+proceso.name()+" "+proceso.status()+" "+proceso.username()+" "+proceso.exe()+" ".join(proceso.cmdline())+" "+str(proceso.create_time())+" "+str(proceso.cpu_percent(interval=0.1))+" "+str(proceso.memory_percent())+" "+str(proceso.connections())+str(proceso.threads())+" "+str(proceso.nice())
        print(res)
        info = {
            "PID": pid,
            "Nombre": proceso.name(),
            "Estado": proceso.status(),
            "Usuario": proceso.username(),
            "Executable": proceso.exe(),
            "Argumentos": " ".join(proceso.cmdline()),
            "Tiempo de Creación": proceso.create_time(),
            "Uso de CPU": proceso.cpu_percent(interval=0.1),
            "Uso de Memoria": proceso.memory_percent(),
            "Conexiones de Red": proceso.connections(),
            "Hijos": proceso.children(),
            #"Rutas de Archivos Abiertos": proceso.open_files(),
            #"Threads": proceso.threads(),
            #"Terminal": proceso.terminal(),
           # "Nice value": proceso.nice(),
            "Prioridad": proceso.nice(),
            # ... otras propiedades que desees obtener
        }
        
        informacion_completa = " ".join(f"{clave}: {valor}" for clave,valor in info.items())
        return res
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return f"No se encontró el proceso con PID {pid}"
    
def guardar_en_base_de_datos(catalogo, procesos):
    connection = db
    cursor = connection.cursor()

    # Guardar el catálogo en la tabla 'catalogo'
    cursor.execute("INSERT INTO catalogo (descripcion, nombre, prioridad, usuario) VALUES (%s, %s, %s, %s)",
                   (catalogo["descripcion"], catalogo["nombre"], catalogo["prioridad"], catalogo["usuario"]))
    connection.commit()
    catalogo_id = cursor.lastrowid

    # Guardar los procesos en la tabla 'procesos'
    for proceso in procesos:
        cursor.execute("INSERT INTO procesos (catalogo_id, descripcion, nombre, pid, prioridad, usuario) VALUES (%s, %s, %s, %s, %s, %s)",
                       (catalogo_id, proceso["descripcion"], proceso["nombre"], proceso["pid"], proceso["prioridad"], proceso["usuario"]))
        connection.commit()

    cursor.close()
    connection.close()

    
@app.route('/getProcesos/<orden>/<int:cantidad>', methods=['GET'])
def get_procesos(orden, cantidad):
    procesos = obtener_procesos(orden, cantidad)
    return jsonify(procesos)

@app.route('/guardarCatalogo', methods=['POST'])
def guardar_catalogo():
    data = request.get_json()
    catalogo = data['catalogo']
    procesos = data['procesos']

    # Insertar el catálogo en la base de datos
    #cursor.execute("INSERT INTO catalogos (nombre) VALUES (%s)", (catalogo,))
    #catalogo_id = cursor.lastrowid

    # Insertar los procesos en la base de datos
    for proceso in procesos:
        descripcion = proceso.get("descripcion")
        nombre = proceso.get("nombre")
        pid = proceso.get("pid")
        prioridad = proceso.get("prioridad")
        if(proceso.get("usuario") == None):
            usuario = "null"
        else:
            usuario = proceso.get("usuario")

        cursor.execute("INSERT INTO proceso (descripcion, nombre, pid, prioridad, usuario, nombre_cat,id_usuario) VALUES (%s, %s, %s, %s, %s, %s,%s)",
                       (descripcion, nombre, pid, prioridad, usuario, catalogo,"duortega"))

    db.commit()

    return jsonify({"mensaje": "Catálogo y procesos guardados correctamente"})

@app.route('/consultarCategorias', methods=['GET'])
def consultar_categorias():
    # Consultar procesos en la base de datos según el catálogo
    cursor.execute("SELECT nombre_cat, COUNT(*) as cantidad FROM proceso GROUP BY nombre_cat")
    procesos = cursor.fetchall()

    # Verificar si no se encontraron procesos para el catálogo dado
    if not procesos:
        return jsonify({"mensaje": "No se encontraron procesos para el catálogo proporcionado"}), 404

    # Formatear y devolver los resultados como una lista de diccionarios
    resultado = []
    for proceso in procesos:
        print(proceso)
        resultado.append({
            "nombre_cat": proceso[0],
            "cantidad": proceso[1]
        })

    return jsonify(resultado)

@app.route('/consultarProcesos/<codCatalogo>', methods=['GET'])
def consultar_procesos(codCatalogo):
    # Consultar procesos en la base de datos según el catálogo
    cursor.execute("SELECT * FROM proceso WHERE nombre_cat = %s",(codCatalogo,))
    procesos = cursor.fetchall()

    # Verificar si no se encontraron procesos para el catálogo dado
    if not procesos:
        return jsonify({"mensaje": "No se encontraron procesos para el catálogo proporcionado"}), 404

    # Formatear y devolver los resultados como una lista de diccionarios
    resultado = []
    for proceso in procesos:
        print(proceso)
        resultado.append({
            "descripcion": proceso[3],
            "nombre": proceso[4],
            "pid": proceso[5],
            "prioridad": proceso[6],
            "usuario": proceso[7]
        })

    return jsonify(resultado)

if __name__ == '__main__':
    app.run(debug=True)
