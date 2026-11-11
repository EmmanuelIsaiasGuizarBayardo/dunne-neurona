# Estación «Escuchar a la multitud»

Guion de actividad para **Misión NeuroTech: tecnologías que están transformando
el estudio del cerebro**, y plantilla para eventos del mismo formato.

| | |
|---|---|
| Duración | 10 minutos por grupo |
| Grupo | unas 40 personas, todas las edades |
| Ritmo | grupos sucesivos todo el día |
| Equipo | una tablet por persona, mural proyectado |
| Personal | dos: quien narra y quien opera el mural |

---

## La pregunta de la estación

La misión pregunta cómo estudian los científicos el cerebro sin verlo
funcionar. Esta estación responde una parte concreta: **¿cómo es posible
escuchar al cerebro desde fuera de la cabeza?**

La respuesta es la sincronía. Un electrodo sobre el cuero cabelludo no puede
oír a una neurona sola. Solo detecta algo cuando una población enorme se activa
al mismo tiempo, porque la actividad dispersa se cancela. Las personas del
grupo lo descubren siendo esas neuronas.

### Lugar dentro de la misión

Esta estación es la **antesala de NeuroDAC**. Aquí, cuarenta personas
descubren por qué se puede medir la actividad cerebral; en NeuroDAC, una
persona la mide en su propia cabeza con una diadema de EEG. Conviene que el
recorrido las ponga en ese orden, y el cierre de esta estación invita a pasar a
la otra.

---

## Objetivo de aprendizaje

Al salir, cada persona puede decir con sus palabras:

> El cerebro se puede escuchar desde fuera porque muchas neuronas trabajan al
> mismo tiempo. Una sola no se oye.

Una idea, no tres. En diez minutos no caben más.

---

## Guion

### 0:00 · Llegada

El grupo entra y toma una tablet. Ya están encendidas, conectadas y con el
tipo de neurona bloqueado. En el mural se ve la onda plana.

**Quien narra:**
> Cada uno de ustedes tiene en las manos una neurona. Cuando la tocan, le
> llega una señal. Mírenla en su pantalla.

### 1:00 · Cada quien a su ritmo

> Tóquenla las veces que quieran, como quieran.

El mural muestra una onda baja, nerviosa, sin forma. El raster se llena de
marcas dispersas.

> Miren arriba. Eso es lo que oiría un aparato que escucha al cerebro desde
> afuera. Hay mucha actividad, pero no se distingue nada.

### 3:00 · El reto

Quien opera lanza el juego de **Sincronía**.

> La neurona del centro solo se activa si la mitad de ustedes la toca al
> mismo tiempo. Inténtenlo.

El primer intento casi nunca sale. No hay que ayudar todavía.

### 4:30 · El descubrimiento

Lo primero que casi todos intentan es tocar sin parar. **No funciona, y es a
propósito**: cada tablet muestra una barra, *tu sinapsis*, que se vacía con
cada toque y solo se recupera al esperar. El mural muestra cuántas personas
están tocando y cuánto valen en realidad: pueden ser treinta tocando que entre
todas valen dos.

> Están tocando mucho, pero sus sinapsis se cansaron. Así les pasa a las
> neuronas de verdad cuando se las estimula sin descanso.

Alguien propone esperar y contar. Si nadie lo propone en un minuto, quien
narra pregunta:

> ¿Qué necesitan para tocar todos al mismo tiempo?

Con la cuenta regresiva, el grupo lo logra. **En la onda aparece un pico
enorme**, unas tres o cuatro veces más alto que todo lo anterior.

Ese es el momento de la estación. Hay que dejarlo respirar un segundo antes de
explicar.

### 5:30 · La explicación

> Lo que acaban de ver es la razón por la que existe el electroencefalograma.
> Un aparato en la cabeza no puede oír a una neurona sola, igual que ustedes no
> se notaban cuando cada quien tocaba a su ritmo. Pero cuando miles de
> neuronas se activan juntas, la señal es tan grande que se oye desde fuera.

### 6:30 · El ritmo

> Ahora no una vez: toquen juntos, todos al mismo tiempo, una y otra vez,
> como si aplaudieran siguiendo una canción.

Quien narra marca el pulso con la voz o con palmas, más o menos uno por
segundo. **La onda deja de ser un pico y se vuelve una oscilación**: sube y baja
con el ritmo del grupo.

> Esto es una onda cerebral. Cuando muchas neuronas se sincronizan una y otra
> vez con un ritmo, el EEG ve una onda que sube y baja. Su cerebro produce
> ondas así ahora mismo, con distintos ritmos según si están despiertos,
> concentrados o dormidos.

Es el segundo momento fuerte de la estación, y conecta directo con lo que van a
ver en NeuroDAC.

### 7:30 · Cierre

> En la siguiente estación van a ver esa misma onda, pero la de su propio
> cerebro, con una diadema que la mide de verdad.

Y la pregunta que conecta con el final de la misión:

> Si pudiéramos leer esa onda, ¿qué harían con ella?

Las respuestas se anotan: son materia prima para la reunión final donde se
imaginan las neurotecnologías del futuro. Esa pregunta es, literalmente, la que
dio origen a las interfaces cerebro-computadora.

### 9:00 · Salida

Las tablets se dejan en su lugar. El código QR de la neurona queda proyectado
para quien quiera seguir explorando en casa.

---

## Para quien opera el mural

| momento | acción en la consola |
|---|---|
| antes del grupo | *Reiniciar voltajes*. Confirmar que el censo marca 40. *Bloquear tipos* activo. |
| 3:00 | *Sincronía* |
| 6:30 | Sin cambios; el juego sigue activo |
| 9:00 | *Detener* y *Reiniciar voltajes* para el grupo siguiente |

Reposición entre grupos: unos 40 segundos. No se consume material.

---

## Para quien narra: lo que conviene saber

Estas notas son para el personal, no para decirlas al público.

**La onda del mural es una simulación, y está construida con cuidado.** Cada
toque es una entrada sináptica que produce un potencial postsináptico con
subida y bajada. La suma de toda la sala pasa por un filtro pasa-altas, como en
cualquier amplificador de EEG, lo que hace que la señal oscile alrededor de
cero en lugar de acumularse.

**La amplitud depende del número absoluto de personas sincronizadas**, no de la
proporción. Una sola tablet produce una onda diminuta aunque esté sola en la
sala; así funciona el EEG real. Por eso, para probar el mural con un solo
dispositivo, conviene abrir la página de neurona en varias pestañas: cada una
cuenta como una persona.

**Una sola sincronía produce un transitorio**, parecido a un potencial evocado.
**La sincronía repetida con ritmo produce una oscilación**, que es como se
originan los ritmos del EEG. Si alguien pregunta por qué la onda no es
sinusoidal desde el principio, esa es la respuesta.

**Se suman entradas, no disparos**, porque el EEG registra potenciales
postsinápticos sumados y no potenciales de acción. Si alguien con formación
pregunta, esa es la respuesta precisa, y la simulación es fiel a ella.

**Lo que sí es una simplificación:** en el cerebro, las neuronas que más
contribuyen al EEG son las piramidales de la corteza, alineadas en paralelo, y
la cantidad necesaria para producir una señal detectable es muchísimo mayor que
cuarenta. El principio, que solo la actividad sincrónica es visible desde
fuera, se sostiene.

**Por qué tocar sin parar no sirve.** Cada toque gasta una parte de los
recursos de la sinapsis, que se recuperan en unos segundos. Es la depresión
sináptica a corto plazo: con estimulación repetida, el botón sináptico se queda
sin vesículas listas para liberar y cada estímulo produce menos efecto. Tsodyks
y Markram (1997) mostraron que cuando esta depresión es rápida, la neurona
postsináptica deja de responder a cuánto disparan sus entradas y responde a qué
tan sincronizadas llegan. Es exactamente lo que el juego exige.

Medido con el servidor real y 40 participantes durante un minuto: con la regla
anterior, tocar sin parar lograba 62 disparos y la cuenta regresiva solo 15;
con la depresión, tocar sin parar logra uno, el inicial, y la cuenta regresiva
conserva sus 15. Cinco personas que no paran no arruinan el esfuerzo de las
otras 35, pero si la mitad del salón no coopera, no se logra.

**Si el primer intento sale bien a la primera**, el grupo es especialmente
coordinado o alguien ya conocía la dinámica. Conviene subir el reto pidiendo
que lo logren sin contar en voz alta.

### Referencia

Tsodyks, M. V., & Markram, H. (1997). The neural code between neocortical
pyramidal neurons depends on neurotransmitter release probability.
*Proceedings of the National Academy of Sciences, 94*(2), 719–723.
https://doi.org/10.1073/pnas.94.2.719

---

## Si falla la red

La misma lección sin tecnología. Hay que tenerla ensayada, no escrita.

Todo el grupo aplaude, cada quien a su ritmo. Se escucha un ruido sin forma.

> Así suena el cerebro cuando cada neurona va por su lado.

Luego se pide un aplauso al mismo tiempo, con cuenta regresiva. Un golpe
fuerte, claro, que se oye en toda la sala.

> Así suena cuando se sincronizan. Por eso podemos escucharlo desde fuera.

El oído hace exactamente el papel del electrodo, y la lección es idéntica.

---

## Variante: excitación contra inhibición

Para grupos que repiten o para estudiantes mayores. El salón se divide en dos
equipos que empujan el potencial de la neurona compartida en sentidos
opuestos: uno la acerca al umbral y el otro la aleja.

Enseña que la neurona **suma** lo que la excita y lo que la frena. Tiene un
tope de tres toques por segundo por persona, para que gane el equipo donde más
gente participa y no donde alguien es más rápido. Sin ese tope, el juego lo
gana el equipo con más niños.

No reemplaza a la actividad principal: enseña otra idea, y diez minutos solo
alcanzan para una.

---

## Para reutilizar este guion en otro evento

La estructura funciona con otras preguntas de neurociencias:

1. **Una pregunta del evento**, traducida a una sola idea.
2. **Algo que el grupo hace** y que produce un dato visible.
3. **Un primer intento que falla**, para que haya algo que descubrir.
4. **El momento del descubrimiento**, sin explicación previa.
5. **La explicación**, después y nunca antes.
6. **Una pregunta abierta** que conecte con el resto del evento.

El paso 3 es el que más se tiende a quitar por miedo a que el grupo se
frustre, y es el que hace que el paso 4 importe.
