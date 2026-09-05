from logger import log_info, log_warning, log_error


class FileManager:
    def __init__(self):
        # Diccionario principal: { filename: {"content": str, "owner_pid": int | None} }
        self.filesystem = {}

        # Registro de concurrencia: { filename: pid } — solo el proceso que abrió el archivo
        self.file_locks = {}

        # Contadores de operaciones para monitoreo
        self.total_operations = 0
        self.failed_operations = 0

    # ── Método privado de validación de bloqueo ────────────────────────────────
    def _check_lock(self, filename, pid):
        """
        Devuelve (True, None) si el archivo está libre o le pertenece al pid.
        Devuelve (False, mensaje) si otro proceso lo tiene bloqueado.
        """
        holder = self.file_locks.get(filename)
        if holder is not None and holder != pid:
            return False, (
                f"[ERROR] Acceso denegado: el archivo '{filename}' está en uso "
                f"por el proceso PID={holder}. PID={pid} debe esperar."
            )
        return True, None

    # ── 1. create_file ─────────────────────────────────────────────────────────
    def create_file(self, filename, pid):
        """
        Crea un archivo vacío en el sistema virtual.
        Rechaza la operación si el nombre ya existe o si otro proceso lo bloquea.
        """
        try:
            self.total_operations += 1

            # Si el archivo ya existe, verificar bloqueo antes de reportar duplicado
            if filename in self.filesystem:
                ok, err = self._check_lock(filename, pid)
                if not ok:
                    self.failed_operations += 1
                    log_warning(err)
                    return err
                msg = f"[ERROR] El archivo '{filename}' ya existe. Operación cancelada."
                self.failed_operations += 1
                log_warning(msg)
                return msg

            # Crear el archivo y asignarlo al proceso creador
            self.filesystem[filename] = {"content": "", "owner_pid": pid}
            self.file_locks[filename] = pid

            msg = f"[OK] Archivo '{filename}' creado exitosamente por PID={pid}."
            log_info(msg)
            return msg

        except Exception as e:
            self.failed_operations += 1
            msg = f"[EXCEPCIÓN] create_file falló de forma inesperada: {e}"
            log_error(msg)
            return msg

    # ── 2. read_file ───────────────────────────────────────────────────────────
    def read_file(self, filename, pid):
        """
        Lee el contenido de un archivo.
        Permite lectura concurrente siempre que ningún proceso tenga escritura exclusiva.
        Si el archivo está bloqueado por otro pid en modo escritura, rechaza.
        """
        try:
            self.total_operations += 1

            if filename not in self.filesystem:
                msg = f"[ERROR] El archivo '{filename}' no existe."
                self.failed_operations += 1
                log_warning(msg)
                return msg

            ok, err = self._check_lock(filename, pid)
            if not ok:
                self.failed_operations += 1
                log_warning(err)
                return err

            content = self.filesystem[filename]["content"]
            preview = content if content else "<vacio>"
            msg = f"[OK] PID={pid} leyó '{filename}': {preview}"
            log_info(msg)
            return msg

        except Exception as e:
            self.failed_operations += 1
            msg = f"[EXCEPCIÓN] read_file falló de forma inesperada: {e}"
            log_error(msg)
            return msg

    # ── 3. write_file ──────────────────────────────────────────────────────────
    def write_file(self, filename, pid, content=""):
        """
        Escribe contenido en un archivo existente.
        Bloquea el archivo para uso exclusivo del pid durante la escritura.
        Al terminar la escritura el bloqueo se mantiene hasta que el proceso lo libere
        (o hasta que se destruya el FileManager), reflejando que el archivo queda abierto.
        """
        try:
            self.total_operations += 1

            if filename not in self.filesystem:
                msg = f"[ERROR] El archivo '{filename}' no existe. Créalo primero."
                self.failed_operations += 1
                log_warning(msg)
                return msg

            ok, err = self._check_lock(filename, pid)
            if not ok:
                self.failed_operations += 1
                log_warning(err)
                return err

            # Adquirir bloqueo exclusivo y escribir
            self.file_locks[filename] = pid
            self.filesystem[filename]["content"] += content
            self.filesystem[filename]["owner_pid"] = pid

            msg = f"[OK] PID={pid} escribió en '{filename}'. Contenido actual: '{self.filesystem[filename]['content']}'"
            log_info(msg)
            return msg

        except Exception as e:
            self.failed_operations += 1
            msg = f"[EXCEPCIÓN] write_file falló de forma inesperada: {e}"
            log_error(msg)
            return msg

    # ── 4. move_file ───────────────────────────────────────────────────────────
    def move_file(self, old_name, new_name, pid):
        """
        Renombra / mueve un archivo dentro del sistema virtual.
        Requiere que el archivo origen exista y que ningún otro proceso lo bloquee.
        El nuevo nombre no debe colisionar con un archivo existente bloqueado por otro pid.
        """
        try:
            self.total_operations += 1

            if old_name not in self.filesystem:
                msg = f"[ERROR] El archivo origen '{old_name}' no existe."
                self.failed_operations += 1
                log_warning(msg)
                return msg

            ok, err = self._check_lock(old_name, pid)
            if not ok:
                self.failed_operations += 1
                log_warning(err)
                return err

            if new_name in self.filesystem:
                ok2, err2 = self._check_lock(new_name, pid)
                if not ok2:
                    self.failed_operations += 1
                    log_warning(err2)
                    return err2
                msg = f"[ERROR] Ya existe un archivo con el nombre '{new_name}'. Elige otro nombre."
                self.failed_operations += 1
                log_warning(msg)
                return msg

            # Trasladar contenido y bloqueos al nuevo nombre
            self.filesystem[new_name] = self.filesystem.pop(old_name)
            self.file_locks[new_name] = self.file_locks.pop(old_name, pid)
            self.filesystem[new_name]["owner_pid"] = pid

            msg = f"[OK] PID={pid} movio/renombro '{old_name}' -> '{new_name}'."
            log_info(msg)
            return msg

        except Exception as e:
            self.failed_operations += 1
            msg = f"[EXCEPCIÓN] move_file falló de forma inesperada: {e}"
            log_error(msg)
            return msg

    # ── 5. delete_file ─────────────────────────────────────────────────────────
    def delete_file(self, filename, pid):
        """
        Elimina un archivo del sistema virtual.
        Solo el proceso propietario (o si el archivo está libre) puede eliminarlo.
        """
        try:
            self.total_operations += 1

            if filename not in self.filesystem:
                msg = f"[ERROR] El archivo '{filename}' no existe."
                self.failed_operations += 1
                log_warning(msg)
                return msg

            ok, err = self._check_lock(filename, pid)
            if not ok:
                self.failed_operations += 1
                log_warning(err)
                return err

            del self.filesystem[filename]
            self.file_locks.pop(filename, None)

            msg = f"[OK] PID={pid} eliminó el archivo '{filename}' correctamente."
            log_info(msg)
            return msg

        except Exception as e:
            self.failed_operations += 1
            msg = f"[EXCEPCIÓN] delete_file falló de forma inesperada: {e}"
            log_error(msg)
            return msg

    # ── Método auxiliar: liberar bloqueo manualmente ───────────────────────────
    def release_file(self, filename, pid):
        """
        Libera el bloqueo que un proceso tiene sobre un archivo.
        Útil para simular el cierre de un archivo por parte del proceso.
        """
        try:
            self.total_operations += 1

            if filename not in self.filesystem:
                msg = f"[ERROR] El archivo '{filename}' no existe."
                self.failed_operations += 1
                log_warning(msg)
                return msg

            holder = self.file_locks.get(filename)

            # Archivo sin bloqueo activo
            if holder is None:
                msg = f"[ERROR] El archivo '{filename}' no tiene ningún bloqueo activo; no hay nada que liberar."
                self.failed_operations += 1
                log_warning(msg)
                return msg

            # El pid solicitante no es el propietario actual
            if holder != pid:
                msg = (
                    f"[ERROR] PID={pid} no puede liberar '{filename}' "
                    f"porque no es su propietario actual (propietario: PID={holder})."
                )
                self.failed_operations += 1
                log_warning(msg)
                return msg

            self.file_locks.pop(filename, None)
            msg = f"[OK] PID={pid} liberó el bloqueo sobre '{filename}'."
            log_info(msg)
            return msg

        except Exception as e:
            self.failed_operations += 1
            msg = f"[EXCEPCIÓN] release_file falló de forma inesperada: {e}"
            log_error(msg)
            return msg

    # ── Método auxiliar: estado general del sistema ────────────────────────────
    def get_status(self):
        """
        Devuelve un resumen del estado actual del sistema de archivos virtual.
        """
        return {
            "total_files": len(self.filesystem),
            "locked_files": {f: pid for f, pid in self.file_locks.items()},
            "total_operations": self.total_operations,
            "failed_operations": self.failed_operations,
        }
