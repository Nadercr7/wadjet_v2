"""Comprehensive Gardiner Sign List -> transliteration mapping.

Maps 700+ Gardiner codes to their transliteration values, sign types,
and descriptions. This is the core Egyptological reference data.

Sources:
- Gardiner, A.H. (1957) Egyptian Grammar, 3rd ed., Sign List pp.438-548
- Allen, J.P. (2014) Middle Egyptian, 3rd ed., pp.423-478
- Collier & Manley (1998) How to Read Egyptian Hieroglyphs
- JSesh sign database / Unicode Egyptian Hieroglyphs block documentation

Sign Types:
- UNILITERAL: single-consonant phonogram (alphabet, ~26 signs)
- BILITERAL: two-consonant phonogram (~80 signs)
- TRILITERAL: three-consonant phonogram (~60 signs)
- LOGOGRAM: represents a whole word (ideogram)
- DETERMINATIVE: silent classifier that indicates word meaning category
- ABBREVIATION: logogram that can also have phonetic value
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class SignType(Enum):
    UNILITERAL = "uniliteral"
    BILITERAL = "biliteral"
    TRILITERAL = "triliteral"
    LOGOGRAM = "logogram"
    DETERMINATIVE = "determinative"
    ABBREVIATION = "abbreviation"
    NUMBER = "number"


@dataclass
class GardinerSign:
    """Complete data for a single Gardiner sign."""
    code: str                        # e.g. "G1"
    transliteration: str             # e.g. "A" (Manuel de Codage)
    sign_type: SignType              # uniliteral, biliteral, etc.
    description: str                 # e.g. "Egyptian vulture"
    category: str                    # Gardiner category letter (A-Z, Aa)
    phonetic_value: str              # MdC transliteration
    logographic_value: str = ""      # word meaning when used as logogram
    determinative_class: str = ""    # semantic class when used as determinative
    unicode_char: str = ""           # Unicode code point if available
    alt_transliterations: list[str] | None = None  # alternate readings


# ═══════════════════════════════════════════════════════════
# UNILITERAL SIGNS (Egyptian "alphabet" - ~26 consonants)
# These are the most important: each represents one consonant.
# ═══════════════════════════════════════════════════════════

UNILITERALS: dict[str, GardinerSign] = {
    "G1": GardinerSign("G1", "A", SignType.UNILITERAL, "Egyptian vulture", "G",
                        "A", unicode_char="\U00013171"),
    "M17": GardinerSign("M17", "i", SignType.UNILITERAL, "reed", "M",
                         "i", unicode_char="\U000131CB"),
    "M18": GardinerSign("M18", "ii", SignType.UNILITERAL, "two reeds", "M",
                         "y", alt_transliterations=["ii", "y"]),
    "D36": GardinerSign("D36", "a", SignType.UNILITERAL, "forearm", "D",
                         "a", unicode_char="\U00013091"),
    "G43": GardinerSign("G43", "w", SignType.UNILITERAL, "quail chick", "G",
                         "w", unicode_char="\U0001319F"),
    "D58": GardinerSign("D58", "b", SignType.UNILITERAL, "foot", "D",
                         "b", unicode_char="\U000130B0"),
    "Q3": GardinerSign("Q3", "p", SignType.UNILITERAL, "stool", "Q",
                        "p", unicode_char="\U00013249"),
    "I9": GardinerSign("I9", "f", SignType.UNILITERAL, "horned viper", "I",
                        "f", unicode_char="\U000131AB"),
    "G17": GardinerSign("G17", "m", SignType.UNILITERAL, "owl", "G",
                         "m", unicode_char="\U00013186"),
    "N35": GardinerSign("N35", "n", SignType.UNILITERAL, "water ripple", "N",
                         "n", unicode_char="\U00013216"),
    "D21": GardinerSign("D21", "r", SignType.UNILITERAL, "mouth", "D",
                         "r", unicode_char="\U00013072"),
    "O4": GardinerSign("O4", "h", SignType.UNILITERAL, "reed shelter", "O",
                        "h", unicode_char="\U00013229"),
    "V28": GardinerSign("V28", "H", SignType.UNILITERAL, "wick", "V",
                         "H", unicode_char="\U000132A3"),
    "Aa1": GardinerSign("Aa1", "x", SignType.UNILITERAL, "placenta(?)", "Aa",
                          "x"),
    "S29": GardinerSign("S29", "s", SignType.UNILITERAL, "folded cloth", "S",
                         "s", unicode_char="\U00013282"),
    "N37": GardinerSign("N37", "S", SignType.UNILITERAL, "pool", "N",
                         "S", unicode_char="\U0001321A"),
    "V13": GardinerSign("V13", "T", SignType.UNILITERAL, "tethering rope", "V",
                         "T", unicode_char="\U00013294"),
    "D46": GardinerSign("D46", "d", SignType.UNILITERAL, "hand", "D",
                         "d", unicode_char="\U000130A0"),
    "I10": GardinerSign("I10", "D", SignType.UNILITERAL, "cobra", "I",
                         "D", unicode_char="\U000131AC"),
    "X1": GardinerSign("X1", "t", SignType.UNILITERAL, "bread loaf", "X",
                        "t", unicode_char="\U000132B4"),
    "V31": GardinerSign("V31", "k", SignType.UNILITERAL, "basket with handle", "V",
                         "k", unicode_char="\U000132A8"),
    "W11": GardinerSign("W11", "g", SignType.UNILITERAL, "jar stand", "W",
                         "g", unicode_char="\U000132AE"),
    # Aa2 is an alternate for x -- some encode as Aa2
    "F35": GardinerSign("F35", "nfr", SignType.TRILITERAL, "heart & windpipe", "F",
                         "nfr", logographic_value="good, beautiful"),
    # Additional uniliterals sometimes listed:
    "D4": GardinerSign("D4", "ir", SignType.BILITERAL, "eye", "D",
                        "ir", logographic_value="eye; to do, make"),
    "D19": GardinerSign("D19", "fnD", SignType.TRILITERAL, "nose", "D",
                         "fnD", logographic_value="nose"),
}


# ═══════════════════════════════════════════════════════════
# BILITERAL SIGNS (two consonant values)
# ═══════════════════════════════════════════════════════════

BILITERALS: dict[str, GardinerSign] = {
    "D4": GardinerSign("D4", "ir", SignType.BILITERAL, "eye", "D", "ir",
                        logographic_value="eye"),
    "D28": GardinerSign("D28", "kA", SignType.BILITERAL, "two raised arms", "D", "kA",
                         logographic_value="ka (spirit)"),
    "D34": GardinerSign("D34", "aS", SignType.BILITERAL, "arms in gesture of negation", "D", "aS"),
    "D35": GardinerSign("D35", "nw", SignType.BILITERAL, "arms with vessel", "D", "nw"),
    "D39": GardinerSign("D39", "mH", SignType.BILITERAL, "forearm with bowl", "D", "mH"),
    "D52": GardinerSign("D52", "mt", SignType.BILITERAL, "phallus", "D", "mt"),
    "D53": GardinerSign("D53", "mw", SignType.BILITERAL, "phallus with liquid", "D", "mw"),
    "D54": GardinerSign("D54", "wrd", SignType.DETERMINATIVE, "legs walking", "D", "",
                         determinative_class="motion, walking"),
    "D56": GardinerSign("D56", "rd", SignType.BILITERAL, "leg", "D", "rd",
                         logographic_value="leg, foot"),
    "D60": GardinerSign("D60", "wab", SignType.TRILITERAL, "vessel between legs", "D", "wab"),
    "D62": GardinerSign("D62", "mt", SignType.BILITERAL, "toes", "D", "mt"),
    "E1": GardinerSign("E1", "kA", SignType.LOGOGRAM, "bull", "E", "kA",
                        logographic_value="bull"),
    "E9": GardinerSign("E9", "sAb", SignType.TRILITERAL, "sacred baboon", "E", "sAb"),
    "E17": GardinerSign("E17", "mAi", SignType.TRILITERAL, "lion", "E", "mAi",
                         logographic_value="lion"),
    "E23": GardinerSign("E23", "rwD", SignType.TRILITERAL, "lying lion", "E", "rwD"),
    "E34": GardinerSign("E34", "SA", SignType.BILITERAL, "hare", "E", "SA"),
    "F4": GardinerSign("F4", "kA", SignType.BILITERAL, "forepart of lion", "F", "kA",
                        logographic_value="bull"),
    "F9": GardinerSign("F9", "nSm", SignType.TRILITERAL, "horns with sun-disc", "F", "nSm"),
    "F12": GardinerSign("F12", "wsr", SignType.TRILITERAL, "head and neck of animal", "F", "wsr",
                         logographic_value="mighty"),
    "F13": GardinerSign("F13", "wp", SignType.BILITERAL, "horns", "F", "wp",
                         logographic_value="open"),
    "F16": GardinerSign("F16", "db", SignType.BILITERAL, "horn", "F", "db"),
    "F18": GardinerSign("F18", "ns", SignType.BILITERAL, "tusk", "F", "ns"),
    "F21": GardinerSign("F21", "sDm", SignType.TRILITERAL, "ear", "F", "sDm",
                         logographic_value="to hear"),
    "F22": GardinerSign("F22", "Hw", SignType.BILITERAL, "hindquarters of lion", "F", "Hw"),
    "F23": GardinerSign("F23", "xnt", SignType.TRILITERAL, "foreleg of ox", "F", "xnt"),
    "F26": GardinerSign("F26", "Hn", SignType.BILITERAL, "goat skin", "F", "Hn"),
    "F29": GardinerSign("F29", "sti", SignType.TRILITERAL, "cattle-skin with arrow", "F", "sti"),
    "F30": GardinerSign("F30", "sD", SignType.BILITERAL, "water-skin", "F", "sD"),
    "F31": GardinerSign("F31", "ms", SignType.BILITERAL, "three fox-skins", "F", "ms",
                         logographic_value="birth"),
    "F32": GardinerSign("F32", "xm", SignType.BILITERAL, "waste matter from belly", "F", "xm"),
    "F34": GardinerSign("F34", "ib", SignType.BILITERAL, "heart", "F", "ib",
                         logographic_value="heart"),
    "F40": GardinerSign("F40", "Aw", SignType.BILITERAL, "backbone with ribs", "F", "Aw",
                         logographic_value="length"),
    "G4": GardinerSign("G4", "tyw", SignType.TRILITERAL, "buzzard", "G", "tyw"),
    "G5": GardinerSign("G5", "Hr", SignType.LOGOGRAM, "Horus falcon", "G", "Hr",
                        logographic_value="Horus"),
    "G7": GardinerSign("G7", "Hr", SignType.DETERMINATIVE, "falcon on standard", "G", "",
                        determinative_class="god, divine"),
    "G10": GardinerSign("G10", "tA", SignType.BILITERAL, "falcon on basket", "G", "tA"),
    "G14": GardinerSign("G14", "mwt", SignType.TRILITERAL, "vulture", "G", "mwt",
                         logographic_value="mother"),
    "G21": GardinerSign("G21", "nH", SignType.BILITERAL, "guinea fowl", "G", "nH"),
    "G24": GardinerSign("G24", "rxyt", SignType.LOGOGRAM, "lapwing", "G", "rxyt",
                         logographic_value="common people, subjects"),
    "G25": GardinerSign("G25", "Ax", SignType.BILITERAL, "crested ibis", "G", "Ax",
                         logographic_value="glory, spirit"),
    "G26": GardinerSign("G26", "bA", SignType.BILITERAL, "sacred ibis", "G", "bA",
                         logographic_value="ba-soul"),
    "G29": GardinerSign("G29", "bA", SignType.BILITERAL, "jabiru", "G", "bA"),
    "G35": GardinerSign("G35", "aq", SignType.BILITERAL, "cormorant", "G", "aq"),
    "G36": GardinerSign("G36", "wr", SignType.BILITERAL, "swallow", "G", "wr",
                         logographic_value="great"),
    "G37": GardinerSign("G37", "nDs", SignType.TRILITERAL, "sparrow", "G", "nDs"),
    "G39": GardinerSign("G39", "sA", SignType.BILITERAL, "pintail duck", "G", "sA"),
    "G40": GardinerSign("G40", "pA", SignType.BILITERAL, "flying pintail", "G", "pA"),
    "G50": GardinerSign("G50", "pAq", SignType.TRILITERAL, "two plovers", "G", "pAq"),
    "H6": GardinerSign("H6", "mAat", SignType.TRILITERAL, "feather", "H", "mAat",
                         logographic_value="Maat, truth"),
    "I5": GardinerSign("I5", "Hfn", SignType.TRILITERAL, "winding serpent", "I", "Hfn"),
    "L1": GardinerSign("L1", "xpr", SignType.TRILITERAL, "scarab beetle", "L", "xpr",
                        logographic_value="Khepri; to become"),
    "M1": GardinerSign("M1", "xt", SignType.BILITERAL, "tree", "M", "xt",
                        logographic_value="tree, wood"),
    "M3": GardinerSign("M3", "Ht", SignType.BILITERAL, "branch", "M", "Ht"),
    "M4": GardinerSign("M4", "rnp", SignType.TRILITERAL, "palm branch", "M", "rnp",
                        logographic_value="year"),
    "M8": GardinerSign("M8", "SA", SignType.BILITERAL, "lotus pool", "M", "SA"),
    "M12": GardinerSign("M12", "xA", SignType.BILITERAL, "lotus plant", "M", "xA"),
    "M16": GardinerSign("M16", "HA", SignType.BILITERAL, "clump of papyrus", "M", "HA"),
    "M20": GardinerSign("M20", "sw", SignType.BILITERAL, "reed & loaf", "M", "sw"),
    "M23": GardinerSign("M23", "sw", SignType.BILITERAL, "sedge plant", "M", "sw",
                         logographic_value="king of Upper Egypt"),
    "M26": GardinerSign("M26", "Sma", SignType.TRILITERAL, "flowering sedge", "M", "Sma"),
    "M29": GardinerSign("M29", "nDm", SignType.TRILITERAL, "pod", "M", "nDm"),
    "M40": GardinerSign("M40", "is", SignType.BILITERAL, "bundle of reeds", "M", "is"),
    "M41": GardinerSign("M41", "Hsa", SignType.TRILITERAL, "piece of wood", "M", "Hsa"),
    "M42": GardinerSign("M42", "sn", SignType.BILITERAL, "flower", "M", "sn"),
    "M44": GardinerSign("M44", "sp", SignType.BILITERAL, "thorn", "M", "sp"),
    "N1": GardinerSign("N1", "pt", SignType.BILITERAL, "sky", "N", "pt",
                        logographic_value="sky, heaven"),
    "N2": GardinerSign("N2", "pt", SignType.DETERMINATIVE, "sky with sceptre", "N", "",
                        determinative_class="sky, heaven"),
    "N5": GardinerSign("N5", "ra", SignType.LOGOGRAM, "sun disc", "N", "ra",
                        logographic_value="Ra; sun; day"),
    "N14": GardinerSign("N14", "sbA", SignType.TRILITERAL, "star", "N", "sbA",
                         logographic_value="star"),
    "N16": GardinerSign("N16", "tA", SignType.LOGOGRAM, "flat land", "N", "tA",
                         logographic_value="land, earth"),
    "N17": GardinerSign("N17", "tA", SignType.LOGOGRAM, "land with grain", "N", "tA"),
    "N18": GardinerSign("N18", "iw", SignType.BILITERAL, "sandy tract", "N", "iw"),
    "N19": GardinerSign("N19", "iw", SignType.BILITERAL, "two sandy tracts", "N", "iw"),
    "N24": GardinerSign("N24", "spAt", SignType.TRILITERAL, "irrigation canal scheme", "N", "spAt",
                         logographic_value="nome, district"),
    "N25": GardinerSign("N25", "xAst", SignType.TRILITERAL, "three hills", "N", "xAst",
                         logographic_value="foreign land"),
    "N26": GardinerSign("N26", "Dw", SignType.BILITERAL, "mountain", "N", "Dw",
                         logographic_value="mountain"),
    "N29": GardinerSign("N29", "qA", SignType.BILITERAL, "slope of hill", "N", "qA",
                         logographic_value="high"),
    "N30": GardinerSign("N30", "Dba", SignType.TRILITERAL, "mound with plants", "N", "Dba"),
    "N31": GardinerSign("N31", "wAt", SignType.TRILITERAL, "road with shrubs", "N", "wAt",
                         logographic_value="road"),
    "N36": GardinerSign("N36", "mr", SignType.BILITERAL, "canal", "N", "mr"),
    "N41": GardinerSign("N41", "Hm", SignType.BILITERAL, "well with water", "N", "Hm"),
    "O1": GardinerSign("O1", "pr", SignType.BILITERAL, "house", "O", "pr",
                        logographic_value="house"),
    "O4": GardinerSign("O4", "h", SignType.UNILITERAL, "reed shelter", "O", "h"),
    "O11": GardinerSign("O11", "aH", SignType.BILITERAL, "palace", "O", "aH",
                         logographic_value="palace"),
    "O28": GardinerSign("O28", "iwn", SignType.TRILITERAL, "column", "O", "iwn"),
    "O29": GardinerSign("O29", "aA", SignType.BILITERAL, "peg", "O", "aA"),
    "O31": GardinerSign("O31", "Htp", SignType.TRILITERAL, "door", "O", "Htp"),
    "O34": GardinerSign("O34", "s", SignType.UNILITERAL, "door bolt", "O", "s",
                         alt_transliterations=["z"]),
    "O49": GardinerSign("O49", "niwt", SignType.LOGOGRAM, "city", "O", "niwt",
                         logographic_value="city, town"),
    "O50": GardinerSign("O50", "Ssp", SignType.TRILITERAL, "threshing floor", "O", "Ssp"),
    "O51": GardinerSign("O51", "niwt", SignType.LOGOGRAM, "heap of grain", "O", "niwt"),
    "P1": GardinerSign("P1", "dp", SignType.BILITERAL, "boat", "P", "dp"),
    "P6": GardinerSign("P6", "mxnt", SignType.TRILITERAL, "mast", "P", "mxnt"),
    "P8": GardinerSign("P8", "xAw", SignType.TRILITERAL, "oar", "P", "xAw"),
    "Q1": GardinerSign("Q1", "st", SignType.BILITERAL, "seat/throne", "Q", "st",
                        logographic_value="throne; place"),
    "Q7": GardinerSign("Q7", "snTr", SignType.TRILITERAL, "brazier", "Q", "snTr",
                        logographic_value="incense"),
    "R4": GardinerSign("R4", "Htp", SignType.TRILITERAL, "offering loaf on mat", "R", "Htp",
                        logographic_value="offering; peace"),
    "R8": GardinerSign("R8", "nTr", SignType.TRILITERAL, "cloth on pole", "R", "nTr",
                        logographic_value="god"),
    "S24": GardinerSign("S24", "TAw", SignType.TRILITERAL, "knot", "S", "TAw"),
    "S28": GardinerSign("S28", "Dba", SignType.TRILITERAL, "sash", "S", "Dba"),
    "S34": GardinerSign("S34", "anx", SignType.TRILITERAL, "ankh", "S", "anx",
                         logographic_value="life; to live"),
    "S42": GardinerSign("S42", "wAs", SignType.TRILITERAL, "was sceptre", "S", "wAs",
                         logographic_value="dominion"),
    "T14": GardinerSign("T14", "qmA", SignType.TRILITERAL, "throwstick", "T", "qmA"),
    "T20": GardinerSign("T20", "nmt", SignType.TRILITERAL, "harpoon head", "T", "nmt"),
    "T21": GardinerSign("T21", "Hq", SignType.BILITERAL, "harpoon", "T", "Hq"),
    "T22": GardinerSign("T22", "Ss", SignType.BILITERAL, "arrowhead", "T", "Ss"),
    "T28": GardinerSign("T28", "sfx", SignType.TRILITERAL, "butcher's block", "T", "sfx"),
    "T30": GardinerSign("T30", "nm", SignType.BILITERAL, "knife", "T", "nm"),
    "U1": GardinerSign("U1", "mA", SignType.BILITERAL, "sickle", "U", "mA"),
    "U7": GardinerSign("U7", "mr", SignType.BILITERAL, "hoe", "U", "mr"),
    "U15": GardinerSign("U15", "tm", SignType.BILITERAL, "sledge", "U", "tm"),
    "U28": GardinerSign("U28", "DA", SignType.BILITERAL, "fire-drill", "U", "DA"),
    "U33": GardinerSign("U33", "ti", SignType.BILITERAL, "pestle", "U", "ti"),
    "U35": GardinerSign("U35", "nmt", SignType.TRILITERAL, "grain measure", "U", "nmt"),
    "V4": GardinerSign("V4", "wA", SignType.BILITERAL, "lasso", "V", "wA"),
    "V6": GardinerSign("V6", "Ss", SignType.BILITERAL, "cord on stick", "V", "Ss"),
    "V7": GardinerSign("V7", "snT", SignType.TRILITERAL, "winding cord", "V", "snT"),
    "V16": GardinerSign("V16", "sA", SignType.BILITERAL, "hobble", "V", "sA"),
    "V22": GardinerSign("V22", "mn", SignType.BILITERAL, "string", "V", "mn"),
    "V24": GardinerSign("V24", "wD", SignType.BILITERAL, "amulet string", "V", "wD"),
    "V25": GardinerSign("V25", "wAD", SignType.TRILITERAL, "string with seal", "V", "wAD"),
    "V28": GardinerSign("V28", "H", SignType.UNILITERAL, "wick", "V", "H"),
    "V30": GardinerSign("V30", "nb", SignType.BILITERAL, "basket", "V", "nb",
                         logographic_value="lord; every"),
    "V31": GardinerSign("V31", "k", SignType.UNILITERAL, "basket with handle", "V", "k"),
    "W14": GardinerSign("W14", "Hz", SignType.BILITERAL, "water-jar", "W", "Hz"),
    "W15": GardinerSign("W15", "iab", SignType.TRILITERAL, "water-jar with legs", "W", "iab"),
    "W18": GardinerSign("W18", "kAb", SignType.TRILITERAL, "water-jar with handles", "W", "kAb"),
    "W19": GardinerSign("W19", "mi", SignType.BILITERAL, "milk-jug with handle", "W", "mi"),
    "W22": GardinerSign("W22", "ab", SignType.BILITERAL, "beer-jug", "W", "ab"),
    "W24": GardinerSign("W24", "nw", SignType.BILITERAL, "pot", "W", "nw"),
    "W25": GardinerSign("W25", "ini", SignType.TRILITERAL, "pot with legs", "W", "ini"),
    "X6": GardinerSign("X6", "pAt", SignType.TRILITERAL, "round loaf", "X", "pAt",
                        logographic_value="cake"),
    "X8": GardinerSign("X8", "di", SignType.BILITERAL, "conical loaf", "X", "di",
                        logographic_value="to give"),
    "Y1": GardinerSign("Y1", "mDAt", SignType.TRILITERAL, "papyrus roll", "Y", "mDAt",
                        determinative_class="writing, abstract"),
    "Y2": GardinerSign("Y2", "mnhd", SignType.TRILITERAL, "papyrus roll (sealed)", "Y", "mnhd"),
    "Y3": GardinerSign("Y3", "sS", SignType.BILITERAL, "scribe's kit", "Y", "sS",
                        logographic_value="scribe; writing"),
    "Y5": GardinerSign("Y5", "mn", SignType.BILITERAL, "game board", "Y", "mn",
                        logographic_value="senet"),
    "Z1": GardinerSign("Z1", "|", SignType.NUMBER, "single stroke", "Z", "",
                        logographic_value="1; ideogram indicator"),
    "Z7": GardinerSign("Z7", "W", SignType.ABBREVIATION, "coil", "Z", "W",
                        alt_transliterations=["w"]),
    "Z11": GardinerSign("Z11", "imi", SignType.TRILITERAL, "two crossed planks", "Z", "imi"),
    # Extended / less common signs in our model:
    "A55": GardinerSign("A55", "Hs", SignType.BILITERAL, "mummy on bed", "A", "Hs",
                         determinative_class="death"),
    "Aa15": GardinerSign("Aa15", "wDa", SignType.TRILITERAL, "unknown", "Aa", "wDa"),
    "Aa26": GardinerSign("Aa26", "uncertain", SignType.LOGOGRAM, "unknown", "Aa", ""),
    "Aa27": GardinerSign("Aa27", "nD", SignType.BILITERAL, "unknown", "Aa", "nD"),
    "Aa28": GardinerSign("Aa28", "qd", SignType.BILITERAL, "unknown", "Aa", "qd"),
    "D1": GardinerSign("D1", "tp", SignType.BILITERAL, "head", "D", "tp",
                        logographic_value="head"),
    "D2": GardinerSign("D2", "Hr", SignType.BILITERAL, "face", "D", "Hr",
                        logographic_value="face; upon"),
    "D10": GardinerSign("D10", "wDAt", SignType.TRILITERAL, "Eye of Horus", "D", "wDAt",
                         logographic_value="Eye of Horus; well-being"),
    "D156": GardinerSign("D156", "uncertain", SignType.LOGOGRAM, "rare body part sign", "D", ""),
    "M195": GardinerSign("M195", "uncertain", SignType.LOGOGRAM, "rare plant sign", "M", ""),
    "P13": GardinerSign("P13", "xrw", SignType.TRILITERAL, "steering oar", "P", "xrw"),
    "P98": GardinerSign("P98", "uncertain", SignType.LOGOGRAM, "rare boat sign", "P", ""),
}

# Merge all into a single lookup
GARDINER_TRANSLITERATION: dict[str, GardinerSign] = {}
GARDINER_TRANSLITERATION.update(UNILITERALS)
GARDINER_TRANSLITERATION.update(BILITERALS)  # May override some from UNILITERALS


def get_transliteration(gardiner_code: str) -> str:
    """Get the transliteration for a Gardiner code.

    Returns the phonetic_value if the sign has one, or the transliteration
    field, or the code itself as a fallback.
    """
    sign = GARDINER_TRANSLITERATION.get(gardiner_code)
    if sign is None:
        return f"[{gardiner_code}]"  # Unknown sign

    if sign.phonetic_value:
        return sign.phonetic_value
    if sign.transliteration:
        return sign.transliteration
    return f"[{gardiner_code}]"


def get_sign_type(gardiner_code: str) -> SignType:
    """Get the type of a Gardiner sign."""
    sign = GARDINER_TRANSLITERATION.get(gardiner_code)
    if sign is None:
        return SignType.LOGOGRAM  # default for unknown
    return sign.sign_type


def is_determinative(gardiner_code: str) -> bool:
    """Check if a Gardiner sign is primarily used as a determinative."""
    sign = GARDINER_TRANSLITERATION.get(gardiner_code)
    if sign is None:
        return False
    return sign.sign_type == SignType.DETERMINATIVE or bool(sign.determinative_class)


def get_determinative_class(gardiner_code: str) -> str:
    """Get the semantic class for a determinative sign."""
    sign = GARDINER_TRANSLITERATION.get(gardiner_code)
    if sign is None:
        return ""
    return sign.determinative_class


# ── Determinative categories (common semantic classifiers) ──

DETERMINATIVE_CATEGORIES: dict[str, list[str]] = {
    "man/person": ["A1", "A2", "A3", "A40", "A50", "A55", "B1"],
    "god/divine": ["G7", "R8", "C1", "C2"],
    "motion/walking": ["D54"],
    "death/enemy": ["A55", "Z6"],
    "negation": ["D35"],
    "abstract": ["Y1", "Y2"],
    "writing": ["Y1", "Y3"],
    "sky/above": ["N1", "N2"],
    "land/earth": ["N16", "N17", "N25"],
    "water": ["N35", "N36"],
    "city/place": ["O49", "O51"],
    "house/building": ["O1"],
    "eye/sight": ["D4", "D10"],
    "mouth/speech": ["D21"],
}

# Reverse mapping: sign -> determinative categories
SIGN_TO_DET_CATEGORIES: dict[str, list[str]] = {}
for _cat, _signs in DETERMINATIVE_CATEGORIES.items():
    for _s in _signs:
        SIGN_TO_DET_CATEGORIES.setdefault(_s, []).append(_cat)


# ═══════════════════════════════════════════════════════════
# Unicode character mapping (Egyptian Hieroglyphs block U+13000-U+1342F)
# Auto-generated from Unicode 15.0 standard character names.
# ═══════════════════════════════════════════════════════════

_GARDINER_UNICODE: dict[str, str] = {
    "A55": "\U00013040",
    "Aa1": "\U0001340D",
    "Aa15": "\U0001341D",
    "Aa26": "\U00013428",
    "Aa27": "\U00013429",
    "Aa28": "\U0001342A",
    "D1": "\U00013076",
    "D10": "\U00013080",
    "D19": "\U00013089",
    "D2": "\U00013077",
    "D28": "\U00013093",
    "D34": "\U0001309A",
    "D35": "\U0001309C",
    "D39": "\U000130A0",
    "D4": "\U00013079",
    "D52": "\U000130B8",
    "D53": "\U000130BA",
    "D54": "\U000130BB",
    "D56": "\U000130BE",
    "D60": "\U000130C2",
    "D62": "\U000130C4",
    "E1": "\U000130D2",
    "E17": "\U000130E5",
    "E23": "\U000130ED",
    "E34": "\U000130F9",
    "E9": "\U000130DB",
    "F12": "\U0001310A",
    "F13": "\U0001310B",
    "F16": "\U0001310F",
    "F18": "\U00013111",
    "F21": "\U00013114",
    "F22": "\U00013116",
    "F23": "\U00013117",
    "F26": "\U0001311A",
    "F29": "\U0001311D",
    "F30": "\U0001311E",
    "F31": "\U0001311F",
    "F32": "\U00013121",
    "F34": "\U00013123",
    "F35": "\U00013124",
    "F4": "\U00013102",
    "F40": "\U0001312B",
    "F9": "\U00013107",
    "G10": "\U0001314B",
    "G14": "\U00013150",
    "G21": "\U00013158",
    "G25": "\U0001315C",
    "G26": "\U0001315D",
    "G29": "\U00013161",
    "G35": "\U00013167",
    "G36": "\U00013168",
    "G37": "\U0001316A",
    "G39": "\U0001316D",
    "G4": "\U00013142",
    "G40": "\U0001316E",
    "G5": "\U00013143",
    "G50": "\U0001317A",
    "G7": "\U00013146",
    "H6": "\U00013184",
    "I5": "\U0001318C",
    "L1": "\U000131A3",
    "M1": "\U000131AD",
    "M12": "\U000131BC",
    "M16": "\U000131C9",
    "M18": "\U000131CD",
    "M20": "\U000131CF",
    "M23": "\U000131D3",
    "M26": "\U000131D7",
    "M29": "\U000131DB",
    "M3": "\U000131B1",
    "M4": "\U000131B3",
    "M40": "\U000131E9",
    "M41": "\U000131EB",
    "M42": "\U000131EC",
    "M44": "\U000131EE",
    "M8": "\U000131B7",
    "N1": "\U000131EF",
    "N14": "\U000131FC",
    "N16": "\U000131FE",
    "N17": "\U000131FF",
    "N18": "\U00013200",
    "N19": "\U00013203",
    "N2": "\U000131F0",
    "N24": "\U00013208",
    "N25": "\U00013209",
    "N26": "\U0001320B",
    "N29": "\U0001320E",
    "N30": "\U0001320F",
    "N31": "\U00013210",
    "N36": "\U00013218",
    "N41": "\U0001321E",
    "N5": "\U000131F3",
    "O1": "\U00013250",
    "O11": "\U00013265",
    "O28": "\U0001327A",
    "O29": "\U0001327B",
    "O31": "\U0001327F",
    "O34": "\U00013283",
    "O4": "\U00013254",
    "O49": "\U00013296",
    "O50": "\U00013297",
    "O51": "\U0001329A",
    "P1": "\U0001329B",
    "P6": "\U000132A2",
    "P8": "\U000132A4",
    "Q1": "\U000132A8",
    "Q7": "\U000132AE",
    "R4": "\U000132B5",
    "R8": "\U000132B9",
    "S24": "\U000132ED",
    "S28": "\U000132F3",
    "S34": "\U000132F9",
    "S42": "\U00013302",
    "T14": "\U00013319",
    "T20": "\U00013320",
    "T21": "\U00013321",
    "T22": "\U00013322",
    "T28": "\U00013328",
    "T30": "\U0001332A",
    "U1": "\U00013333",
    "U15": "\U00013343",
    "U28": "\U00013351",
    "U33": "\U00013358",
    "U35": "\U0001335A",
    "U7": "\U0001333B",
    "V16": "\U00013382",
    "V22": "\U00013394",
    "V24": "\U00013397",
    "V25": "\U00013398",
    "V28": "\U0001339B",
    "V30": "\U0001339F",
    "V31": "\U000133A1",
    "V4": "\U0001336F",
    "V6": "\U00013371",
    "V7": "\U00013372",
    "W14": "\U000133BF",
    "W15": "\U000133C1",
    "W18": "\U000133C5",
    "W19": "\U000133C7",
    "W22": "\U000133CA",
    "W24": "\U000133CC",
    "W25": "\U000133CE",
    "X6": "\U000133D6",
    "X8": "\U000133D9",
    "Y1": "\U000133DB",
    "Y2": "\U000133DD",
    "Y3": "\U000133DE",
    "Y5": "\U000133E0",
    "Z1": "\U000133E4",
    "Z11": "\U000133F6",
    "Z7": "\U000133F2",
    # Non-standard extended signs — approximated with closest related glyph
    "D156": "\U000130A7",  # ≈ D046 (finger/hand — body part group)
    "M195": "\U000131AD",  # ≈ M001 (tree — plant group)
    "P13": "\U000132A4",   # ≈ P008 (oar — ship equipment group)
    "P98": "\U0001329B",   # ≈ P001 (boat — ship group)
}

# Backfill unicode_char on signs that were defined without one
for _code, _char in _GARDINER_UNICODE.items():
    if _code in GARDINER_TRANSLITERATION:
        sign = GARDINER_TRANSLITERATION[_code]
        if not sign.unicode_char:
            sign.unicode_char = _char
