import { useEffect, useState } from "react";

// Estado de conexion del dispositivo. La operacion en terreno tiene senal
// intermitente (R2): la UI reacciona a online/offline.
export function useOnline(): boolean {
  const [online, setOnline] = useState<boolean>(
    typeof navigator !== "undefined" ? navigator.onLine : true,
  );

  useEffect(() => {
    const subir = () => setOnline(true);
    const bajar = () => setOnline(false);
    window.addEventListener("online", subir);
    window.addEventListener("offline", bajar);
    return () => {
      window.removeEventListener("online", subir);
      window.removeEventListener("offline", bajar);
    };
  }, []);

  return online;
}
