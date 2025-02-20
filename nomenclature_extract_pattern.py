import re


nomenclature_pattern = [
    # Шаблоны для извлечения чисел
    # Формат с * (16g*24pcs*12boxes)
    (
        r"(\d+(?:[.,]\d+)?)(?:g|gr|gx|г|гр|грам|грамм|G|GR|ml|мл)\s*[*]\s*(\d+)(?:\s*(?:pcs|pc|шт|p))?\s*[*]\s*(\d+)",
        lambda m: (exctract_float(m.group(1)), int(m.group(2)), int(m.group(3))),
    ),
    # Формат с * и GR (6GR*6*12)
    (
        r"(\d+(?:[.,]\d+)?)(?:GR|gr|g|G)\s*[*]\s*(\d+)\s*[*]\s*(\d+)",
        lambda m: (exctract_float(m.group(1)), int(m.group(2)), int(m.group(3))),
    ),
    # Формат без разделителей (16g24pcs12boxes)
    (
        r"(\d+(?:[.,]\d+)?)(?:g|gr|gx|г|гр|грам|грамм|G|GR|ml|мл)(\d+)(?:pcs|pc|шт|p)?(\d+)(?:boxes|box|jars|jar|tray|trays|vase|vases|bag|bags)",
        lambda m: (exctract_float(m.group(1)), int(m.group(2)), int(m.group(3))),
    ),
    # Формат с весом в начале и конце (500g ... 500Gx 8Boxes)
    (
        r"(?:^|\s)(\d+(?:[.,]\d+)?)\s*(?:g|gr|gx|г|гр|грам|грамм|G|GR|ml|мл).*?(\d+)\s*(?:g|gr|gx|г|гр|грам|грамм|G|GR|ml|мл)\s*[xXхХ*]\s*(\d+)(?:\s|boxes|box|$)",
        lambda m: (exctract_float(m.group(2)), 1, int(m.group(3))),
    ),
    # Формат с запятой или точкой (3,5 GX24X8)
    (
        r"(\d+(?:[.,]\d+)?)\s*(?:g|gr|gx|г|гр|грам|грамм|G|GR|ml|мл)[xXхХ*]\s*(\d+)[xXхХ*]\s*(\d+)",
        lambda m: (
            exctract_float(m.group(1)),
            int(m.group(2)),
            int(m.group(3)),
        ),
    ),
    # Формат BLOX (12,5 гр 20 Х 30 бл)
    (
        r"(\d+(?:[.,]\d+)?)\s*(?:г|гр|грам|грамм|gr|g|G|GR|мл|ml)\s+(\d+)\s*[хХxX]\s*(\d+)\s*(?:бл|блок|boxes|box)",
        lambda m: (
            exctract_float(m.group(1)),
            int(m.group(2)),
            int(m.group(3)),
        ),
    ),
    # Формат с размерами (10X48X28G)
    (
        r"(\d+)\s*[xXхХ]\s*(\d+)\s*[xXхХ]\s*(\d+(?:[.,]\d+)?)\s*(?:g|gr|gx|г|гр|грам|грамм|G|GR|ml|мл)(?:\s|$)",
        lambda m: (exctract_float(m.group(3)), int(m.group(2)), int(m.group(1))),
    ),
    # Формат с единицами измерения (100g x 8 pcs x 12tray)
    (
        r"(\d+(?:[.,]\d+)?)\s*(?:g|gr|gx|г|гр|грам|грамм|G|GR|ml|мл)\s*[xXхХ×]\s*(\d+)(?:\s*(?:pcs|pc|шт|p))?\s*[xXхХ×]\s*(\d+)",
        lambda m: (
            exctract_float(m.group(1)),
            int(m.group(2)),
            int(m.group(3)),
        ),
    ),
    # Формат с × (7g×24pcs×24boxes)
    (
        r"(\d+(?:[.,]\d+)?)\s*(?:g|gr|gx|г|гр|грам|грамм|G|GR|ml|мл)\s*[×]\s*(\d+)(?:\s*(?:pcs|pc|шт|p))?\s*[×]\s*(\d+)",
        lambda m: (
            exctract_float(m.group(1)),
            int(m.group(2)),
            int(m.group(3)),
        ),
    ),
    # Формат с весом и количеством (900grx6)
    (
        r"(\d+(?:[.,]\d+)?)\s*(?:g|gr|gx|г|гр|грам|грамм|ml|мл)[xXхХ*]\s*(\d+)(?:\s|$)",
        lambda m: (exctract_float(m.group(1)), 1, int(m.group(2))),
    ),
    # Формат с GR и числами (6GR612)
    (
        r"(\d+(?:[.,]\d+)?)(?:GR|gr|g|G)(\d+)(\d+)",
        lambda m: (exctract_float(m.group(1)), int(m.group(2)), int(m.group(3))),
    ),
    # Формат с числами через пробел (15g 12 24)
    (
        r"(\d+(?:[.,]\d+)?)(?:g|gr|gx|г|гр|грам|грамм|G|GR|ml|мл)\s+(\d+)\s+(\d+)",
        lambda m: (exctract_float(m.group(1)), int(m.group(2)), int(m.group(3))),
    ),
    # Формат Kokolin (12*24*18gr)
    (
        r"(\d+)\s*[*]\s*(\d+)\s*[*]\s*(\d+(?:[.,]\d+)?)(?:g|gr|gx|г|гр|грам|грамм|G|GR)",
        lambda m: (exctract_float(m.group(3)), int(m.group(2)), int(m.group(1))),
    ),
    # Формат с пробелами и Х (36гр 12шт Х12бл)
    (
        r"(\d+(?:[.,]\d+)?)\s*(?:g|gr|gx|г|гр|грам|грамм|G|GR|ml|мл)\s+(\d+)\s*(?:шт|штХ|шт\s*[xXхХ])\s*[xXхХ]\s*(\d+)\s*(?:бл|блок|блоков)",
        lambda m: (exctract_float(m.group(1)), int(m.group(2)), int(m.group(3))),
    ),
    # Формат с пробелами и слитным штХ (15 гр 20штХ 4бл)
    (
        r"(\d+(?:[.,]\d+)?)\s*(?:g|gr|gx|г|гр|грам|грамм|G|GR|ml|мл)\s+(\d+)\s*штХ\s*(\d+)\s*(?:бл|блок|блоков)",
        lambda m: (exctract_float(m.group(1)), int(m.group(2)), int(m.group(3))),
    ),
    # Новый формат для BISCOLATA DUOMAX FINDIKLI 12KT 12AD 44G
    (
        r"(\d+)\s*KT\s*(\d+)\s*AD\s*(\d+(?:[.,]\d+)?)\s*(?:g|gr|gx|г|гр|грам|грамм|G|GR|ml|мл)",
        lambda m: (exctract_float(m.group(3)), int(m.group(2)), int(m.group(1))),
    ),
    # Новый формат для CRAZY PRINC PATLAK AMB 6KT 24AD 30G KSA
    (
        r"(\d+)\s*KT\s*(\d+)\s*AD\s*(\d+(?:[.,]\d+)?)\s*G\s*[A-Za-zА-Яа-я]+",
        lambda m: (exctract_float(m.group(3)), int(m.group(2)), int(m.group(1))),
    ),
    # Новый формат для BOOMB. H.CV.KAR.PPT. 6KT12ADT35G CIS2
    (
        r"(\d+)\s*KT(\d+)\s*ADT(\d+(?:[.,]\d+)?)\s*G\s*[A-Z]+",
        lambda m: (exctract_float(m.group(3)), int(m.group(2)), int(m.group(1))),
    ),
    # Новый формат для TWINGO KARAMEL 6KT 24AD 42 CIS2
    (
        r"(\d+)\s*KT\s*(\d+)\s*AD\s*(\d+(?:[.,]\d+)?)\s*[A-Z]+",
        lambda m: (exctract_float(m.group(3)), int(m.group(2)), int(m.group(1))),
    ),
    # Новый формат для WINERGY YER FISTIKLI BAR 6KT 24AD 30G
    (
        r"(\d+)\s*KT\s*(\d+)\s*AD\s*(\d+(?:[.,]\d+)?)\s*G",
        lambda m: (exctract_float(m.group(3)), int(m.group(2)), int(m.group(1))),
    ),
    # Новый формат для BOOMBASTIC MARSH.BARKEK 6KT12AD40G UA/RU
    (
        r"(\d+)\s*KT(\d+)\s*AD(\d+(?:[.,]\d+)?)\s*G\s*[A-Z/]+",
        lambda m: (exctract_float(m.group(3)), int(m.group(2)), int(m.group(1))),
    ),
    # Новый формат для LUPPO DREAM BAR KAKAOLU 6KT12AD50G
    (
        r"(\d+)\s*KT(\d+)\s*AD(\d+(?:[.,]\d+)?)\s*G",
        lambda m: (exctract_float(m.group(3)), int(m.group(2)), int(m.group(1))),
    ),
    # Новый формат для OZMO CORNET SUTLU 25G 24 ADT 4KT
    (
        r"(\d+(?:[.,]\d+)?)\s*G\s*(\d+)\s*ADT\s*(\d+)\s*KT",
        lambda m: (exctract_float(m.group(1)), int(m.group(2)), int(m.group(3))),
    ),
    # Новый формат для OZMO CORNET MUZ-DRJ 25G 24ADT4KT TASO AZ
    (
        r"(\d+(?:[.,]\d+)?)\s*G\s*(\d+)\s*ADT(\d+)\s*KT\s*[A-Z]+",
        lambda m: (exctract_float(m.group(1)), int(m.group(2)), int(m.group(3))),
    ),
    # Новый формат для OZMO CORNET G-DRJ 4KT24AD25G YD TASO
    (
        r"(\d+)\s*KT(\d+)\s*AD(\d+(?:[.,]\d+)?)\s*G\s*[A-Z]+",
        lambda m: (exctract_float(m.group(3)), int(m.group(2)), int(m.group(1))),
    ),
    # Новый формат для OZMO CORNET CILEKLI 4KT24AD25G(AR-EN-RO)
    (
        r"(\d+)\s*KT(\d+)\s*AD(\d+(?:[.,]\d+)?)\s*G\s*\([A-Z-]+\)",
        lambda m: (exctract_float(m.group(3)), int(m.group(2)), int(m.group(1))),
    ),
    # Новый формат для BISCOLATA MINIS FINDIKLI GOFRT 24PKT117G
    (
        r"(\d+)\s*PKT(\d+(?:[.,]\d+)?)\s*G",
        lambda m: (exctract_float(m.group(2)), int(m.group(1)), 1),
    ),
    # Новый формат для BOOMB. P.PTKLI FNDKLI GF 6KT12AD32G CIS2
    (
        r"(\d+)\s*KT(\d+)\s*AD(\d+(?:[.,]\d+)?)\s*G\s*[A-Z]+",
        lambda m: (exctract_float(m.group(3)), int(m.group(2)), int(m.group(1))),
    ),
    # Новый формат для TRIPLEX KAPLAMALISZ 6KT 24AD 20G
    (
        r"(\d+)\s*KT\s*(\d+)\s*AD\s*(\d+(?:[.,]\d+)?)\s*G",
        lambda m: (exctract_float(m.group(3)), int(m.group(2)), int(m.group(1))),
    ),
    # Новый формат для SOLEN LUPPO CAKE BITE DARK 12SP 184G(CS)
    (
        r"(\d+)\s*SP\s*(\d+(?:[.,]\d+)?)\s*G\s*\([A-Z]+\)",
        lambda m: (exctract_float(m.group(2)), int(m.group(1)), 1),
    ),
    # Новый формат для LUPPO SANDVIC KAKKEK 6KT 24AD 25G LUBNAN
    (
        r"(\d+)\s*KT\s*(\d+)\s*AD\s*(\d+(?:[.,]\d+)?)\s*G\s*[A-Z]+",
        lambda m: (exctract_float(m.group(3)), int(m.group(2)), int(m.group(1))),
    ),
    # Новый формат для LUPPO VISNE MAR.SNDVIC KEK 12SP 182G Y.T
    (
        r"(\d+)\s*SP\s*(\d+(?:[.,]\d+)?)\s*G\s*[A-Z]+",
        lambda m: (exctract_float(m.group(2)), int(m.group(1)), 1),
    ),
    # Новый формат для SOLEN LUPPO CAKE BITE SADE 12SP 184G(CS)
    (
        r"(\d+)\s*SP\s*(\d+(?:[.,]\d+)?)\s*G\s*\([A-Z]+\)",
        lambda m: (exctract_float(m.group(2)), int(m.group(1)), 1),
    ),
    # Новый формат для LUPPO CAKEBITE CHOCO 6KT24AD25G (UA)
    (
        r"(\d+)\s*KT(\d+)\s*AD(\d+(?:[.,]\d+)?)\s*G\s*\([A-Z]+\)",
        lambda m: (exctract_float(m.group(3)), int(m.group(2)), int(m.group(1))),
    ),
    # Новый формат для LUPPO KARAMEL SNDVICKEK 12SP 182G BALKAN
    (
        r"(\d+)\s*SP\s*(\d+(?:[.,]\d+)?)\s*G\s*[A-Z]+",
        lambda m: (exctract_float(m.group(2)), int(m.group(1)), 1),
    ),
    # Новый формат для Luppo Red Velvet 12SP 182G
    (
        r"(\d+)\s*SP\s*(\d+(?:[.,]\d+)?)\s*G",
        lambda m: (exctract_float(m.group(2)), int(m.group(1)), 1),
    ),
    # Новый формат для BISCOLATA MOOD H.CEVZLI 24PK125G UA/RU
    (
        r"(\d+)\s*PK(\d+(?:[.,]\d+)?)\s*G\s*[A-Z/]+",
        lambda m: (exctract_float(m.group(2)), int(m.group(1)), 1),
    ),
    # Новый формат для OZMO BURGER 6KT 12ADT 40G IHRACAT CS2
    (
        r"(\d+)\s*KT\s*(\d+)\s*ADT\s*(\d+(?:[.,]\d+)?)\s*G\s*[A-Z]+",
        lambda m: (exctract_float(m.group(3)), int(m.group(2)), int(m.group(1))),
    ),
    # Новый формат для OZMO HOPPO CIK. 4KT12ADT40G
    (
        r"(\d+)\s*KT(\d+)\s*ADT(\d+(?:[.,]\d+)?)\s*G",
        lambda m: (exctract_float(m.group(3)), int(m.group(2)), int(m.group(1))),
    ),
    # Новый формат для OZMO HOPPO CIK. 24PK 90G
    (
        r"(\d+)\s*PK\s*(\d+(?:[.,]\d+)?)\s*G",
        lambda m: (exctract_float(m.group(2)), int(m.group(1)), 1),
    ),
    # Новый формат для OZMO HOPPO CILEK 4KT12AD40G (Y.DES)
    (
        r"(\d+)\s*KT(\d+)\s*AD(\d+(?:[.,]\d+)?)\s*G\s*\([A-Z.]+\)",
        lambda m: (exctract_float(m.group(3)), int(m.group(2)), int(m.group(1))),
    ),
    # Новый формат для BISC.MOOD NIGHT 24PK125G(BITTER) UA/RU
    (
        r"(\d+)\s*PK(\d+(?:[.,]\d+)?)\s*G\s*\([A-Z]+\)\s*[A-Z/]+",
        lambda m: (exctract_float(m.group(2)), int(m.group(1)), 1),
    ),
    # Новый формат для BISCOLATA MOOD 24PK 115G
    (
        r"(\d+)\s*PK\s*(\d+(?:[.,]\d+)?)\s*G",
        lambda m: (exctract_float(m.group(2)), int(m.group(1)), 1),
    ),
    # Новый формат для PAPITA PARTY DRJ. SADE BISK 24AD 63G CIS
    (
        r"(\d+)\s*AD\s*(\d+(?:[.,]\d+)?)\s*G\s*[A-Z]+",
        lambda m: (exctract_float(m.group(2)), int(m.group(1)), 1),
    ),
    # Новый формат для PAPITA PARTY DRJ.KAKAOLU BIS24AD 63G CIS
    (
        r"(\d+)\s*AD\s*(\d+(?:[.,]\d+)?)\s*G\s*[A-Z]+",
        lambda m: (exctract_float(m.group(2)), int(m.group(1)), 1),
    ),
    # Новый формат для BISCOLATA STIX SUTLU 4KT 12AD 40G CIS2
    (
        r"(\d+)\s*KT\s*(\d+)\s*AD\s*(\d+)\s*G\s*[A-Z]+",
        lambda m: (exctract_float(m.group(3)), int(m.group(2)), int(m.group(1))),
    ),
    # Новый формат для BISCOLATA STIX H.CEVIZ 4KT 12AD 32G()
    (
        r"(\d+)\s*KT\s*(\d+)\s*AD\s*(\d+)\s*G\s*\(\)",
        lambda m: (exctract_float(m.group(3)), int(m.group(2)), int(m.group(1))),
    ),
    # Новый формат для BISCOLATA STIX P.PATLAKLI 4KT 12AD 34G
    (
        r"(\d+)\s*KT\s*(\d+)\s*AD\s*(\d+)\s*G",
        lambda m: (exctract_float(m.group(3)), int(m.group(2)), int(m.group(1))),
    ),
    # Новый формат для BISCOLATA STIX FINDIKLI 4KT 12AD 32G ()
    (
        r"(\d+)\s*KT\s*(\d+)\s*AD\s*(\d+)\s*G\s*\(\)",
        lambda m: (exctract_float(m.group(3)), int(m.group(2)), int(m.group(1))),
    ),
    # Новый формат для OZMO OGOPOGO CILEKLI KEK 4KT24AD30G
    (
        r"(\d+)\s*KT(\d+)\s*AD(\d+)\s*G",
        lambda m: (exctract_float(m.group(3)), int(m.group(2)), int(m.group(1))),
    ),
    # Новый формат для OZMO OGOPOGO KAK KEK 4KT24AD30G CIS1
    (
        r"(\d+)\s*KT(\d+)\s*AD(\d+)\s*G\s*[A-Z]+",
        lambda m: (exctract_float(m.group(3)), int(m.group(2)), int(m.group(1))),
    ),
    # Новый формат для OZMO FUN HAYVAN SERISI 4KT 24AD 23G
    (
        r"(\d+)\s*KT\s*(\d+)\s*AD\s*(\d+)\s*G",
        lambda m: (exctract_float(m.group(3)), int(m.group(2)), int(m.group(1))),
    ),
    # Новый формат для OZMO FUN YILBASI 12KT24AD23G RTS RU/UA
    (
        r"(\d+)\s*KT(\d+)\s*AD(\d+)\s*G\s*[A-Z]+",
        lambda m: (exctract_float(m.group(3)), int(m.group(2)), int(m.group(1))),
    ),
    # Новый формат для CHOCODANS KARAMEL 4KT12AD125G RUSYA OTO
    (
        r"(\d+)\s*KT(\d+)\s*AD(\d+)\s*G\s*[A-Z]+",
        lambda m: (exctract_float(m.group(3)), int(m.group(2)), int(m.group(1))),
    ),
    # Новый формат для OZMO HOPPO CIK. 4KT*12ADT*40G
    (
        r"(\d+)\s*KT\s*\*\s*(\d+)\s*ADT\s*\*\s*(\d+)\s*G",
        lambda m: (exctract_float(m.group(3)), int(m.group(2)), int(m.group(1))),
    ),
    # ******************
    # Паттерн для "Яйце пластикове сюрприз \"CAR\" з кульками печива в глазурі 8 г 60 шт Х 6"
    (
        r"(\d+(?:[.,]\d+)?)\s*(?:г|гр|грам|грамм|gr|g|G|GR|ml|мл)\s*(\d+)\s*(?:шт|шт\s*[xXхХ])\s*[xXхХ]\s*(\d+)",
        lambda m: (
            exctract_float(m.group(1)),
            int(m.group(2)),
            int(m.group(3)),
        ),
    ),
    # Паттерн для "Шоколадні цукерки BONART CHOCO COINS (монети)в пластиковій банці 100шт 500гр Х12"
    (
        r"(\d+)\s*(?:шт|шт\s*[xXхХ])\s*(\d+(?:[.,]\d+)?)\s*(?:г|гр|грам|грамм|gr|g|G|GR|ml|мл)\s*[xXхХ]\s*(\d+)",
        lambda m: (
            exctract_float(m.group(2)),
            int(m.group(1)),
            int(m.group(3)),
        ),
    ),
    # Паттерн для "Яйце \"Ozmo Egg Faces\" з молочним шоколадом і та сюрпризом УКР 20гр 6блХ 24шт"
    (
        r"(\d+(?:[.,]\d+)?)\s*(?:г|гр|грам|грамм|gr|g|G|GR|ml|мл)\s*(\d+)\s*(?:бл|блок|блоков)\s*[xXхХ]\s*(\d+)\s*(?:шт|шт\s*[xXхХ])",
        lambda m: (
            exctract_float(m.group(1)),
            int(m.group(3)),
            int(m.group(2)),
        ),
    ),
    # Паттерн для "Пудинг зі смаком полуниці 40 грамХ12штХ2бл Kenton"
    (
        r"(\d+(?:[.,]\d+)?)\s*(?:г|гр|грам|грамм|gr|g|G|GR|ml|мл)\s*[xXхХ]\s*(\d+)\s*(?:шт|шт\s*[xXхХ])\s*[xXхХ]\s*(\d+)",
        lambda m: (
            exctract_float(m.group(1)),
            int(m.group(2)),
            int(m.group(3)),
        ),
    ),
    # Паттерн для "Яйце \"Ozmo Egg Faces\" з молочним шоколадом і та сюрпризом 20гр 6блХ 24шт"
    (
        r"(\d+(?:[.,]\d+)?)\s*(?:г|гр|грам|грамм|gr|g|G|GR|ml|мл)\s*(\d+)\s*(?:бл|блок|блоков)\s*[xXхХ]\s*(\d+)\s*(?:шт|шт\s*[xXхХ])",
        lambda m: (
            exctract_float(m.group(1)),
            int(m.group(3)),
            int(m.group(2)),
        ),
    ),
    # Паттерн для "Печиво \"LADYBIRD\" з молочним кремом вкрите молочним, чорним та білим шоколадом 22 г * 24 шт* 6 бл"
    (
        r"(\d+(?:[.,]\d+)?)\s*(?:г|гр|грам|грамм|gr|g|G|GR|ml|мл)\s*[*]\s*(\d+)\s*(?:шт|шт\s*[*])\s*[*]\s*(\d+)\s*(?:бл|блок|блоков)",
        lambda m: (
            exctract_float(m.group(1)),
            int(m.group(2)),
            int(m.group(3)),
        ),
    ),
    # Паттерн для "Яйце пластикове \"TOYS HAPPY EGG\" в жув. гумкою та іграшкою 4гр 24штХ 6"
    (
        r"(\d+(?:[.,]\d+)?)\s*(?:г|гр|грам|грамм|gr|g|G|GR|ml|мл)\s*(\d+)\s*(?:шт|шт\s*[xXхХ])\s*[xXхХ]\s*(\d+)",
        lambda m: (
            exctract_float(m.group(1)),
            int(m.group(2)),
            int(m.group(3)),
        ),
    ),
    # Паттерн для "Печиво \"Simley \" сендвіч з маршмеллоу покрите глазур'ю 19гр.Х 24 Х 6"
    (
        r"(\d+(?:[.,]\d+)?)\s*(?:г|гр|грам|грамм|gr|g|G|GR|ml|мл)\s*[xXхХ]\s*(\d+)\s*[xXхХ]\s*(\d+)",
        lambda m: (
            exctract_float(m.group(1)),
            int(m.group(2)),
            int(m.group(3)),
        ),
    ),
    # Паттерн для "Печиво Papita milky з молочним кремом , мол. шоколадом і кол. драже 12box 24pcs 33g"
    (
        r"(\d+(?:[.,]\d+)?)\s*(?:g|gr|gx|г|гр|грам|грамм|G|GR|ml|мл)\s*(\d+)\s*(?:pcs|pc|шт|p)\s*(\d+)\s*(?:box|boxes|бл|блок|блоков)",
        lambda m: (
            exctract_float(m.group(3)),
            int(m.group(2)),
            int(m.group(1)),
        ),
    ),
    # Паттерн для "Печиво Prens сендвіч з какао кремом та фундуком 25гр 12блХ24шт"
    (
        r"(\d+(?:[.,]\d+)?)\s*(?:г|гр|грам|грамм|gr|g|G|GR|ml|мл)\s*(\d+)\s*(?:бл|блок|блоков)\s*[xXхХ]\s*(\d+)\s*(?:шт|шт\s*[xXхХ])",
        lambda m: (
            exctract_float(m.group(1)),
            int(m.group(3)),
            int(m.group(2)),
        ),
    ),
    # Паттерн для "Печиво \"Simley \" сендвіч з маршмеллоу покрите глазур'ю 19гр.Х 24 Х 6"
    (
        r"(\d+(?:[.,]\d+)?)\s*(?:г|гр|грам|грамм|gr|g|G|GR|ml|мл)\s*[xXхХ]\s*(\d+)\s*[xXхХ]\s*(\d+)",
        lambda m: (exctract_float(m.group(1)), int(m.group(2)), int(m.group(3))),
    ),
    # Паттерн для "Печиво Papita з кокосовим кремом з молочним шоколадом 12box 24pcs 33g"
    (
        r"(\d+(?:[.,]\d+)?)\s*(?:g|gr|gx|г|гр|грам|грамм|G|GR|ml|мл)\s*(\d+)\s*(?:pcs|pc|шт|p)\s*(\d+)\s*(?:box|boxes|бл|блок|блоков)",
        lambda m: (exctract_float(m.group(3)), int(m.group(2)), int(m.group(1))),
    ),
    # Паттерн для извлечения данных из примеров типа "Рулет \"Peki\" с какао кремом 150г*15шт/Хамле №7105"
    (
        r"(\d+(?:[.,]\d+)?)\s*(?:г|гр|грам|грамм|gr|g|G|GR|ml|мл)\s*(?:[.,])?[*xхXХ]\s*(\d+)\s*(?:шт|шт\s*[/])\s*[#\d/]*",
        lambda m: (exctract_float(m.group(1)), 1, int(m.group(2))),
    ),
    # Паттерн для "Шоколадна фігурка \"Ozmo Go\" 30g з молочного, білого та чорного шоколаду 20шт Х 4бл"
    (
        r"(\d+(?:[.,]\d+)?)\s*(?:г|гр|грам|грамм|gr|g|G|GR|ml|мл|кг|kg)\s*(\d+)\s*(?:шт|шт\s*[xXхХ])\s*[xXхХ]\s*(\d+)\s*(?:бл|блок|блоков)",
        lambda m: (exctract_float(m.group(1)), int(m.group(2)), int(m.group(3))),
    ),
    # Паттерн для "Цукерки Драже різнокольорові PASTILLE CONVERSATION HEARTS 142 г Х 24 бл"
    (
        r"(\d+(?:[.,]\d+)?)\s*(?:г|гр|грам|грамм|gr|g|G|GR|ml|мл|кг|kg)\s*[xXхХ]\s*(\d+)\s*(?:бл|блок|блоков)",
        lambda m: (exctract_float(m.group(1)), 1, int(m.group(2))),
    ),
    # Паттерн для "Цукерки жувальні \"Docile ASSORTED PENCILS\" (олівці) з фруктовим смаком у контейнері 1,35 кг * 9 бл"
    (
        r"(\d+(?:[.,]\d+)?)\s*(?:г|гр|грам|грамм|gr|g|G|GR|ml|мл|кг|kg)\s*[*]\s*(\d+)\s*(?:бл|блок|блоков)",
        lambda m: (exctract_float(m.group(1)), 1, int(m.group(2))),
    ),
    # Паттерн для "Цукерки жувальні \"MY TOFEE\" з фруктовим смаком 200шт 1кг Х8"
    (
        r"(\d+(?:[.,]\d+)?)\s*(?:г|гр|грам|грамм|gr|g|G|GR|ml|мл|кг|kg)\s*[xXхХ]\s*(\d+)",
        lambda m: (exctract_float(m.group(1)), int(m.group(2)), 1),
    ),
    # Паттерн для "Цукерки жувальні \"Damla Pencil\" (олівці) з фрукт. смаком у контейнері (150 шт) 1500 г * 8 бл NEW"
    (
        r"(\d+(?:[.,]\d+)?)\s*(?:г|гр|грам|грамм|gr|g|G|GR|ml|мл|кг|kg)\s*[*]\s*(\d+)\s*(?:бл|блок|блоков)",
        lambda m: (exctract_float(m.group(1)), 1, int(m.group(2))),
    ),
    # Паттерн для "Цукерки жувальні \"ADEL TOFIJOYSTICK \" 660 гр.*6шт."
    (
        r"(\d+(?:[.,]\d+)?)\s*(?:г|гр|грам|грамм|gr|g|G|GR|ml|мл|кг|kg)\s*[*]\s*(\d+)\s*(?:шт|шт\s*[.])",
        lambda m: (exctract_float(m.group(1)), int(m.group(2)), 1),
    ),
    # Паттерн для "Цукерки жув \"CANDY METER SOUR BELT STRAWBERRY \" (стрічки) з полуничним смаком в коробці 15 гр 48Х 12"
    (
        r"(\d+(?:[.,]\d+)?)\s*(?:г|гр|грам|грамм|gr|g|G|GR|ml|мл)\s*(\d+)\s*[xXхХ]\s*(\d+)",
        lambda m: (exctract_float(m.group(1)), int(m.group(2)), int(m.group(3))),
    ),
    # Паттерн для "Цукерки льодяник на паличці з жув.гумкою \"AYTOP 3D XXXL MIX \" 30 гр. 80штХ6 бан"
    (
        r"(\d+(?:[.,]\d+)?)\s*(?:г|гр|грам|грамм|gr|g|G|GR|ml|мл)\s*(\d+)\s*(?:шт|шт\s*[xXхХ])\s*[xXхХ]\s*(\d+)\s*(?:бан|бл|блок|блоков)",
        lambda m: (exctract_float(m.group(1)), int(m.group(2)), int(m.group(3))),
    ),
    # Паттерн для "Цукерка \"ORIGINAL.GOURMET\" (настільна стійка) Льодяник асорті 31 гр 120 шт 60 х2 уп"
    (
        r"(\d+(?:[.,]\d+)?)\s*(?:г|гр|грам|грамм|gr|g|G|GR|ml|мл)\s*(\d+)\s*(?:шт|шт\s*[xXхХ])\s*[xXхХ]\s*(\d+)\s*(?:уп|бл|блок|блоков|стенд)",
        lambda m: (exctract_float(m.group(1)), int(m.group(2)), int(m.group(3))),
    ),
    # Паттерн для "Цукерки льодяник на паличці з жув.гумкою \"AYTOP ENERGY GUM \" 30 гр. 80штХ6 бан"
    (
        r"(\d+(?:[.,]\d+)?)\s*(?:г|гр|грам|грамм|gr|g|G|GR|ml|мл)\s*(\d+)\s*(?:шт|шт\s*[xXхХ])\s*[xXхХ]\s*(\d+)\s*(?:бан|бл|блок|блоков)",
        lambda m: (exctract_float(m.group(1)), int(m.group(2)), int(m.group(3))),
    ),
    # Паттерн для "Шоколадна фігурка \"Ozmo Go\" 30g з молочного, білого та чорного шоколаду 20шт Х 4бл"
    (
        r"(\d+(?:[.,]\d+)?)\s*(?:г|гр|грам|грамм|gr|g|G|GR|ml|мл)\s*(\d+)\s*(?:шт|шт\s*[xXхХ])\s*[xXхХ]\s*(\d+)\s*(?:бл|блок|блоков)",
        lambda m: (exctract_float(m.group(1)), int(m.group(2)), int(m.group(3))),
    ),
    # Паттерн для "Цукерки льодяник на паличці \"AYTOP 3D XXL GUM MIX \" 30 гр. на пластиковому стенді 60 штХ6 стенд"
    (
        r"(\d+(?:[.,]\d+)?)\s*(?:г|гр|грам|грамм|gr|g|G|GR|ml|мл)\s*(\d+)\s*(?:шт|шт\s*[xXхХ])\s*[xXхХ]\s*(\d+)\s*(?:стенд|бл|блок|блоков)",
        lambda m: (exctract_float(m.group(1)), int(m.group(2)), int(m.group(3))),
    ),
    # Паттерн для "Цукерки \"Cihan\" 1000гр. X 6шт"
    (
        r"(\d+(?:[.,]\d+)?)\s*(?:г|гр|грам|грамм|gr|g|G|GR|ml|мл)\s*[xXхХ]\s*(\d+)\s*(?:шт|шт\s*[.])",
        lambda m: (exctract_float(m.group(1)), 1, int(m.group(2))),
    ),
    # Паттерн для "Цукерки-льодяники на паличці vil pop \"радуга\" круглый вес 16 гр 6*100"
    (
        r"(\d+(?:[.,]\d+)?)\s*(?:г|гр|грам|грамм|gr|g|G|GR|ml|мл)\s*(\d+)\s*[*]\s*(\d+)",
        lambda m: (exctract_float(m.group(1)), int(m.group(2)), int(m.group(3))),
    ),
    # Паттерн для "Соломка \"JIMMY CREAM CHOCOLATE\" з вершковим кремом 55 гр. 24 штХ4 бл"
    (
        r"(\d+(?:[.,]\d+)?)\s*(?:г|гр|грам|грамм|gr|g|G|GR|ml|мл)\s*(\d+)\s*(?:шт|шт\s*[xXхХ])\s*[xXхХ]\s*(\d+)\s*(?:бл|блок|блоков)",
        lambda m: (exctract_float(m.group(1)), int(m.group(2)), int(m.group(3))),
    ),
    # Паттерн для "Цукерка \"ORIGINAL.GOURMET\" (магн. стійка) Льодяник асорті 31 гр 120 шт 60 х2 уп"
    (
        r"(\d+(?:[.,]\d+)?)\s*(?:г|гр|грам|грамм|gr|g|G|GR|ml|мл)\s*(\d+)\s*(?:шт|шт\s*[xXхХ])\s*[xXхХ]\s*(\d+)\s*(?:уп|бл|блок|блоков)",
        lambda m: (exctract_float(m.group(1)), int(m.group(2)), int(m.group(3))),
    ),
    # Паттерн для "Цукерки льодяник на паличці \"AYTOP FRUTY MIX \" 30 гр. 80штХ6 бан"
    (
        r"(\d+(?:[.,]\d+)?)\s*(?:г|гр|грам|грамм|gr|g|G|GR|ml|мл)\s*(\d+)\s*(?:шт|шт\s*[xXхХ])\s*[xXхХ]\s*(\d+)\s*(?:бан|бл|блок|блоков)",
        lambda m: (exctract_float(m.group(1)), int(m.group(2)), int(m.group(3))),
    ),
    # Паттерн для "Цукерки льодяник на паличці \"AYTOP GUMMY\" 16гр.х100х6"
    (
        r"(\d+(?:[.,]\d+)?)\s*(?:г|гр|грам|грамм|gr|g|G|GR|ml|мл)\s*[xXхХ]\s*(\d+)\s*[xXхХ]\s*(\d+)",
        lambda m: (exctract_float(m.group(1)), int(m.group(2)), int(m.group(3))),
    ),
    # Паттерн для "Цукерки льодяник на паличці \"AYTOP MILKY\" молочний з бананом,полуницею, шоколадом 16гр.х100х6"
    (
        r"(\d+(?:[.,]\d+)?)\s*(?:г|гр|грам|грамм|gr|g|G|GR|ml|мл)\s*[xXхХ]\s*(\d+)\s*[xXхХ]\s*(\d+)",
        lambda m: (exctract_float(m.group(1)), int(m.group(2)), int(m.group(3))),
    ),
    # Паттерн для "Цукерки льодяник на паличці \"AYTOP MIX \" 30 гр. на пластиковому стенді 60 штХ6 стенд"
    (
        r"(\d+(?:[.,]\d+)?)\s*(?:г|гр|грам|грамм|gr|g|G|GR|ml|мл)\s*(\d+)\s*(?:шт|шт\s*[xXхХ])\s*[xXхХ]\s*(\d+)\s*(?:стенд|бл|блок|блоков)",
        lambda m: (exctract_float(m.group(1)), int(m.group(2)), int(m.group(3))),
    ),
    # Паттерн для "Соломка \"JIMMY CREAM CHOCOLATE\" з фісташковим кремом кремом 55 гр. 24 штХ4 бл"
    (
        r"(\d+(?:[.,]\d+)?)\s*(?:г|гр|грам|грамм|gr|g|G|GR|ml|мл)\s*(\d+)\s*(?:шт|шт\s*[xXхХ])\s*[xXхХ]\s*(\d+)\s*(?:бл|блок|блоков)",
        lambda m: (exctract_float(m.group(1)), int(m.group(2)), int(m.group(3))),
    ),
    # Паттерн для "Цукерки льодяник на паличці \"AYTOP CLASSIC\" 11гр.х150х6"
    (
        r"(\d+(?:[.,]\d+)?)\s*(?:г|гр|грам|грамм|gr|g|G|GR|ml|мл)\s*[xXхХ]\s*(\d+)\s*[xXхХ]\s*(\d+)",
        lambda m: (exctract_float(m.group(1)), int(m.group(2)), int(m.group(3))),
    ),
]


def exctract_float(text) -> float:
    import locale

    # Устанавливаем локаль по умолчанию
    locale.setlocale(locale.LC_ALL, "")

    # Получаем системный разделитель дробной части
    decimal_point = locale.localeconv()["decimal_point"]

    return float(text.replace(",", decimal_point).replace(".", decimal_point))
