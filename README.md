# arithmetic and logic (ALU)

### Project waarbij virtueel electronica word nagebouwt die een arithmetic and logic unit simuleren waarop assembly code kan worden uitgevoert.

## Instructies
* **ADD/MIN/Mul:** Basis algebraische instructies.
* **OR/AND/NOT:** Basis logic instructies.
* **JAL:** Bij een JAL instructie gaan we het huidige instruction adres + 1 opslaan in register 15 zodat we na een subroutine kunnen terugspringen naar de plaats waar deze opgeroepen zou zijn.
* **ORI:** Bij een ORI operatie gaan we de inhoud van het register met nummer $rs in een logische OR-gate sturen samen met de immediate value en dat opslaan in $rs. Onze control unit zorgt ervoor dat we kunnen lezen uit register $rs en dat de inhoud van dat register dan naar een OR-gate geleid wordt, samen met de immediate value.
* **LUI:** Bij een Lui operatie gaan we de immediate value met 8 bits naar links shiften en oplaan in register $rs
* **JR:** Bij een JR operatie gaan we verder met de instructie die we vinden op de plaats die bepaald wordt door de inhoud van $rs en de immediate value. De immediate value tellen we bij $rs op. 
* **BNE:** Bij een BNE operaties zal indien rs != rt springen naar het current adres + 1 + immediate value. Zo kunnen er dus bepaalde instructies overslaan worden indien de voorwaarde niet voldaan is.

## Assembly voorbeelden

* **Lucas getallen:** Voorbeeld van recursie waarbij men een reeks Lucas getallen (variant op fibonacci getallen waarbij men als startwaarden 1 en 3 neemt) verkrijgt.
* **sorteer algorithme:** Het sorteren van een array van getallen aan de hand van het bubble sort algoritme.







