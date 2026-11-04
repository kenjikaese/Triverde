from django.test import SimpleTestCase

from common.consola_sql import compactar_sql


class CompactarSqlTests(SimpleTestCase):
    def test_select_sin_lista_de_columnas(self):
        sql = 'SELECT "a"."id", "a"."b" FROM "recepcion_recepcion" WHERE "a"."id" = %s'
        self.assertEqual(
            compactar_sql(sql, (5,)),
            "SELECT ... FROM recepcion_recepcion WHERE id = 5",
        )

    def test_insert_sin_lista_de_columnas(self):
        sql = 'INSERT INTO "recepcion_multa" ("motivo", "monto") VALUES (%s, %s)'
        self.assertEqual(
            compactar_sql(sql, ("Latas", 500)),
            "INSERT INTO recepcion_multa VALUES ('Latas', 500)",
        )

    def test_recorta_sentencias_largas(self):
        self.assertTrue(compactar_sql("UPDATE x SET " + "a" * 400).endswith("..."))
