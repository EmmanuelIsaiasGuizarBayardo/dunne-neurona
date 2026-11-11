# Actividad interactiva de neurociencias

Dinámica de 5 a 10 minutos para grupos de unas 40 personas de todas las
edades, con grupos sucesivos durante todo el día.

**Condiciones confirmadas:** espacio amplio, **una tablet precargada por
persona**, pantalla grande y pantallas auxiliares de apoyo. A futuro, los
asistentes usarán su propio teléfono y habrá una sola pantalla.

---

## Lo que cambia por tener las tablets precargadas

Que cada persona llegue con una tablet encendida y conectada elimina el
obstáculo que normalmente hace inviable una actividad con tecnología en diez
minutos: la conexión. Sin ese costo, **la sala interactiva deja de ser una
opción y pasa a ser la actividad principal**.

Quedan tres restricciones que sí siguen mandando.

**Diez minutos son siete.** Hay que descontar llegada, acomodo y salida. Solo
alcanza para un concepto.

**Se repite todo el día.** La reposición entre grupos cuenta tanto como la
actividad. Todo lo que se consuma hay que reponerlo cada diez minutos, y nadie
va a tener tiempo.

**Todas las edades significa sin lectura obligatoria.** La consigna tiene que
entenderse oyéndola una vez.

Hay además un riesgo nuevo, propio de repartir 40 tablets: **la gente toca
todo**. Si cualquiera puede cambiar su tipo de neurona, en treinta segundos
habrá veinte neuronas inhibitorias y el circuito no hará nada. Por eso existe
el bloqueo de tipo desde el mural.

---

## La actividad principal: la carrera de los dos circuitos

**La idea.** El salón se parte en dos mitades. Cada mitad es un circuito
independiente de unas 20 neuronas. Un circuito está mielinizado y el otro no.
Se dispara la señal en los dos a la vez y se ve cuál llega primero. No hay
competencia entre personas: la diferencia la produce la mielina, y eso es
exactamente lo que se quiere enseñar.

**Qué enseña.** Que la señal tarda, que la demora es medible, y que la mielina
existe para acortarla. Un solo concepto, demostrado con 40 cuerpos y 40
pantallas.

**Por qué funciona con todas las edades.** Cada persona hace una sola cosa:
tocar su pantalla cuando le llega la señal. Un niño de seis años y su abuela
hacen lo mismo, y el niño no tiene ventaja.

### Guion

| tiempo | qué pasa |
|---|---|
| 0:00 | El grupo entra y recoge una tablet. Ya están encendidas y en el circuito. |
| 0:30 | "Cada uno de ustedes es una neurona. Van a formar dos nervios." Se marca la división del salón. |
| 1:30 | Ensayo corto: se dispara en el circuito A y se ve la señal recorrer el mural. |
| 3:00 | Se anuncia que un circuito tiene mielina y el otro no. Se pregunta cuál creen que gana. |
| 4:00 | **La carrera.** Se disparan los dos a la vez. El mural muestra las dos cadenas avanzando. |
| 5:30 | Gana el mielinizado, por mucho. Se muestran los dos tiempos en el raster. |
| 6:30 | Se invierte: ahora el otro circuito tiene la mielina. Se repite. Gana el otro. La causa no era el equipo. |
| 8:00 | Cierre: qué pasa cuando la mielina se daña, y el código QR para seguir en casa. |

El segundo tiro del minuto 6:30 es importante y conviene no saltárselo: sin él,
la mitad que perdió se queda pensando que le tocó el lado malo.

### Qué necesita del software

Las tres funciones que pediste, ya implementadas:

- **Dos circuitos independientes.** La consola reparte los asientos en dos
  mitades que no se conectan entre sí. Una señal del circuito A no puede
  alcanzar al B aunque los asientos sean consecutivos.
- **Cambiar el tipo desde el mural.** El operador decide qué asiento tiene
  mielina y cuál polaridad, sin pedirle nada al público. En la consola, un
  toque sobre la ficha del asiento cambia la polaridad y una pulsación larga
  cambia la mielina.
- **Bloquear el tipo.** Con el bloqueo puesto, las neuronas no pueden
  cambiarse a sí mismas y los botones desaparecen de su pantalla. La regla la
  aplica el servidor, no la interfaz: ocultar un botón no impide que alguien
  mande el mensaje.

### Preparación y reposición

**Antes del día:** router propio, reserva de IP para la laptop, regla de
firewall, tablets con la página añadida a la pantalla de inicio para que
abran sin barra de direcciones.

**Entre grupos, unos 40 segundos:** las tablets se quedan abiertas y
conectadas; basta con *Reiniciar voltajes* desde la consola y confirmar en el
mural que el censo marca 40 neuronas. No se consume ningún material.

**Riesgo principal:** si falla la red no hay actividad. Por eso la siguiente
sección existe.

---

## Los juegos colaborativos

Dos dinámicas que convierten al grupo entero en las entradas de **una sola
neurona compartida**. El resultado depende del grupo, no de una persona. Se
lanzan desde la consola del mural y su medidor se ve en grande sobre el raster.

Durante un juego, tocar la pantalla ya no estimula la neurona propia: cada
toque es una entrada de la neurona compartida. Así se evita que 40 personas
tocando a la vez desaten una avalancha en el circuito.

### Sincronía · la mejor de las dos

La neurona compartida dispara solo si la mitad del grupo toca **dentro del
mismo medio segundo**. Es un concepto real que se llama **detección de
coincidencias**: muchas neuronas disparan únicamente cuando suficientes
entradas llegan juntas.

Lo que la hace la mejor opción para este público: **no se gana con velocidad
sino con coordinación**. Un adulto mayor que toca en el momento justo aporta
exactamente lo mismo que un niño. Nadie puede lograrlo solo, y tocar muchas
veces no sirve.

El medidor muestra cuántas personas van coincidiendo contra el número que hace
falta. La primera vez casi nunca sale; el grupo descubre solo que necesita una
cuenta regresiva, y ese descubrimiento es la mejor parte.

| tiempo | qué pasa |
|---|---|
| 0:00 | "Su neurona solo dispara si la tocan muchos al mismo tiempo." |
| 0:30 | Primer intento libre. Casi nunca alcanza. |
| 1:30 | Alguien propone contar. Con "tres, dos, uno", dispara. |
| 3:00 | Se repite subiendo el reto. |

### Excitación contra inhibición

El salón se parte en dos equipos: uno excitatorio, que empuja el potencial de
la neurona compartida hacia el umbral, y uno inhibitorio, que lo jala hacia
abajo. Si llega al umbral antes de veinte segundos gana la excitación; si no,
la inhibición logró sostenerla.

Enseña lo que de verdad hace una neurona: **sumar** lo que la excita y lo que
la frena, y disparar solo si gana lo primero.

**El riesgo de esta dinámica es que premie la velocidad**, y con un público que
incluye adultos mayores eso significa que gana el equipo con más niños. Por
eso tiene un tope: cada persona cuenta como máximo tres toques por segundo.
Diez toques seguidos de una misma persona valen tres. Así gana el equipo donde
**más gente participa**, no donde alguien teclea más rápido.

Al iniciar, los equipos se forman solos repartiendo los asientos en dos
mitades, y los tipos se bloquean para que nadie se cambie de bando a media
partida. Al detener el juego el bloqueo se libera.

---

## El respaldo sin tecnología: el circuito humano

La misma lección, con cero dependencias. Conviene tenerla ensayada, no
escrita: el día que el router falle, hay que poder cambiar de actividad en
treinta segundos.

El grupo forma una cadena. La señal pasa de uno en uno levantando la mano, y
se cronometra. Luego se "mieliniza": uno de cada cinco se declara nodo de
Ranvier, el resto abre los brazos y hace de vaina, y la señal **solo** la
pasan los nodos. Se vuelve a cronometrar. La diferencia es la misma lección.

Materiales: ninguno. Un cronómetro y voz.

---

## Segunda estación, si hay espacio: ¿uno o dos?

Para una mesa aparte que funcione en paralelo o para la fila de espera.

En parejas, con una pinza de ropa marcada en dos puntas, una persona toca a la
otra en la yema del dedo, en la palma y en el antebrazo. Quien recibe, con los
ojos cerrados, dice si siente una punta o dos. En el dedo distingue dos; en el
antebrazo, con la misma separación, siente una sola.

Enseña que el cuerpo no se siente parejo y que el cerebro dedica muchísima más
superficie a la mano y a la cara. Lleva directo al homúnculo sensorial, que es
una imagen que a todas las edades les resulta memorable.

Veinte pinzas, reutilizables, reposición cero, sin dependencia técnica, y la
sorpresa funciona igual la décima vez que la primera.

---

## Apertura opcional de noventa segundos

Todos aplauden a su propio ritmo, sin instrucción de coordinarse. En menos de
un minuto el grupo converge solo. Se hace notar y luego se pide expresamente
**no** sincronizarse, lo que resulta casi imposible.

Enseña que muchas unidades independientes producen un patrón que nadie
dirigió, que es la intuición de los ritmos cerebrales, y además deja al grupo
atento. Conviene sembrarlo con dos o tres personas del equipo aplaudiendo
firme, porque con un grupo tímido puede no converger.

---

## Programa de diez minutos

| minuto | bloque |
|---|---|
| 0:00 – 1:30 | Llegada, tablets en mano. Aplauso de apertura. |
| 1:30 – 3:00 | Consigna y ensayo del circuito A. |
| 3:00 – 4:00 | Se anuncia la mielina. Apuestas del público. |
| 4:00 – 5:30 | Primera carrera. |
| 5:30 – 6:30 | Los tiempos en el raster. |
| 6:30 – 8:00 | Segunda carrera con la mielina invertida. |
| 8:00 – 10:00 | Cierre, qué pasa al dañarse la mielina, y el QR. |

---

## Cuando sea con teléfonos propios

El plan a futuro cambia una sola cosa, pero es grande: **la conexión vuelve a
costar tiempo**. Con público mixto, lograr que 40 personas abran una liga toma
de tres a cinco minutos, que es la mitad del espacio disponible.

Tres mitigaciones, de menor a mayor esfuerzo:

1. **QR grande y visible desde cualquier punto**, proyectado en la pantalla
   principal desde antes de que el grupo entre, para que se vayan conectando
   mientras se acomodan.
2. **Red propia sin contraseña**, o con una corta escrita en la pantalla.
3. **Una decena de tablets de respaldo** para quien no logre conectarse, que
   siempre habrá alguien.

Aun así conviene asumir que el programa pasará de diez minutos a doce, o que
la carrera se reducirá a un solo tiro.

---

## Qué falta decidir

1. Quién opera el mural. La actividad necesita una persona dedicada a la
   consola que no sea quien narra.
2. Si las tablets se entregan en mano o se dejan en posiciones fijas. Lo
   segundo acelera la reposición entre grupos y evita que se mezclen.
3. Si las pantallas auxiliares repiten el mural o muestran algo distinto; con
   40 personas en un espacio amplio, repetir el mismo mural es lo más probable
   que funcione.
