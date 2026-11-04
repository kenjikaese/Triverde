// Reduce la foto antes de guardarla (CU-27). Una foto de celular pesa varios MB y
// viaja como base64 dentro de la cola local y del lote de sincronizacion (CU-33);
// reducirla aqui evita llenar el dispositivo y gastar datos en terreno.
const LADO_MAXIMO = 1600;
const CALIDAD_JPEG = 0.8;

export async function reducirImagen(archivo: File): Promise<string> {
  const mapa = await createImageBitmap(archivo);
  try {
    const escala = Math.min(1, LADO_MAXIMO / Math.max(mapa.width, mapa.height));
    const lienzo = document.createElement("canvas");
    lienzo.width = Math.round(mapa.width * escala);
    lienzo.height = Math.round(mapa.height * escala);
    const contexto = lienzo.getContext("2d");
    if (!contexto) throw new Error("El dispositivo no pudo procesar la imagen.");
    contexto.drawImage(mapa, 0, 0, lienzo.width, lienzo.height);
    return lienzo.toDataURL("image/jpeg", CALIDAD_JPEG);
  } finally {
    mapa.close();
  }
}
