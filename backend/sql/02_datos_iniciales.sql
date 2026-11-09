--
-- PostgreSQL database dump
--

\restrict JjGgX9JeRUAfDVBEUCiu0gnm8r9azlWQzz3cWHuvMe3aFwzArdiji6VzIABUgcM

-- Dumped from database version 16.15
-- Dumped by pg_dump version 16.15

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Data for Name: acceso_rol; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.acceso_rol (id, nombre, descripcion) VALUES (1, 'Administrador', 'Acceso total: configuracion, mantenedores y reportes.');
INSERT INTO public.acceso_rol (id, nombre, descripcion) VALUES (2, 'Operador', 'Registra recepciones y opera en terreno.');
INSERT INTO public.acceso_rol (id, nombre, descripcion) VALUES (3, 'Transportista', 'Cuenta propia del camionero/arborista (CU-28).');


--
-- Data for Name: configuracion_costooperativo; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.configuracion_costooperativo (id, concepto, monto, unidad, vigente, actualizado_en) VALUES (1, 'Combustible', 1200.00, 'litro', true, '2026-11-07 01:07:54.417465+00');
INSERT INTO public.configuracion_costooperativo (id, concepto, monto, unidad, vigente, actualizado_en) VALUES (2, 'Ayudante', 45000.00, 'hora', true, '2026-11-07 01:07:54.419466+00');


--
-- Data for Name: configuracion_costotransporte; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.configuracion_costotransporte (id, costo_por_km, vigente, fecha) VALUES (1, 2000.00, true, '2026-11-07 01:07:54.414669+00');


--
-- Data for Name: configuracion_parametroconversion; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.configuracion_parametroconversion (id, clave, nombre, valor, unidad, descripcion) VALUES (1, 'alerta_mantenimiento_dias', 'Anticipacion de mantenimiento por fecha', 7.0000, 'dias', 'Dias de anticipacion para generar una alerta de mantenimiento proxima.');
INSERT INTO public.configuracion_parametroconversion (id, clave, nombre, valor, unidad, descripcion) VALUES (2, 'alerta_mantenimiento_horas', 'Anticipacion de mantenimiento por horometro', 50.0000, 'horas', 'Horas de anticipacion para generar una alerta de mantenimiento proxima.');
INSERT INTO public.configuracion_parametroconversion (id, clave, nombre, valor, unidad, descripcion) VALUES (3, 'factor_reduccion_rama', 'Factor de reduccion al triturar rama', 5.0000, ':1', 'Volumenes de rama que se necesitan para obtener 1 volumen de chip al triturar.');
INSERT INTO public.configuracion_parametroconversion (id, clave, nombre, valor, unidad, descripcion) VALUES (4, 'factor_reduccion_tronco', 'Factor de reduccion al triturar tronco', 2.0000, ':1', 'Volumenes de tronco que se necesitan para obtener 1 volumen de chip al triturar.');
INSERT INTO public.configuracion_parametroconversion (id, clave, nombre, valor, unidad, descripcion) VALUES (5, 'factor_multa', 'Factor de multa por material contaminado', 1.0000, ':1', 'Multa proporcional al volumen de material contaminado.');
INSERT INTO public.configuracion_parametroconversion (id, clave, nombre, valor, unidad, descripcion) VALUES (6, 'co2_evitado_camion', 'CO2 evitado por material recibido', 0.0000, 'kg CO2/kg', 'Por definir con el cliente: kg de CO2 que se evitan por cada kg de material recibido.');
INSERT INTO public.configuracion_parametroconversion (id, clave, nombre, valor, unidad, descripcion) VALUES (7, 'co2_evitado_compostaje', 'CO2 evitado por material compostado', 0.0000, 'kg CO2/kg', 'Por definir con el cliente: kg de CO2 que se evitan por cada kg de material compostado.');


--
-- Data for Name: configuracion_tarifarecepcion; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.configuracion_tarifarecepcion (id, tramo_min_m3, tramo_max_m3, monto, vigente) VALUES (1, 0.00, 10.00, 20000.00, true);
INSERT INTO public.configuracion_tarifarecepcion (id, tramo_min_m3, tramo_max_m3, monto, vigente) VALUES (2, 10.00, 20.00, 30000.00, true);
INSERT INTO public.configuracion_tarifarecepcion (id, tramo_min_m3, tramo_max_m3, monto, vigente) VALUES (3, 20.00, 30.00, 40000.00, true);
INSERT INTO public.configuracion_tarifarecepcion (id, tramo_min_m3, tramo_max_m3, monto, vigente) VALUES (4, 30.00, 40.00, 50000.00, true);


--
-- Name: acceso_rol_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.acceso_rol_id_seq', 3, true);


--
-- Name: configuracion_costooperativo_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.configuracion_costooperativo_id_seq', 2, true);


--
-- Name: configuracion_costotransporte_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.configuracion_costotransporte_id_seq', 1, true);


--
-- Name: configuracion_parametroconversion_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.configuracion_parametroconversion_id_seq', 7, true);


--
-- Name: configuracion_tarifarecepcion_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.configuracion_tarifarecepcion_id_seq', 4, true);


--
-- PostgreSQL database dump complete
--

\unrestrict JjGgX9JeRUAfDVBEUCiu0gnm8r9azlWQzz3cWHuvMe3aFwzArdiji6VzIABUgcM

