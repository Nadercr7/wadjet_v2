"""
Wadjet AI — Egyptian Attractions Data Module.

Curated dataset of 20 major Egyptian heritage sites with rich metadata
for the recommendation engine and identification pipeline. Migrated from
legacy app.py and restructured with Pydantic models for type safety.

Service functions bridge the ML classifier class labels to structured
attraction data via ``get_by_class_name()``.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class AttractionType(StrEnum):
    """Category classification for Egyptian heritage sites."""

    PHARAONIC = "Pharaonic"
    ISLAMIC = "Islamic"
    GRECO_ROMAN = "Greco-Roman"
    COPTIC = "Coptic"
    MUSEUM = "Museum"
    NATURAL = "Natural"
    MODERN = "Modern"
    RESORT = "Resort"


class City(StrEnum):
    """Egyptian cities represented in the attractions dataset."""

    CAIRO = "Cairo"
    LUXOR = "Luxor"
    ASWAN = "Aswan"
    ALEXANDRIA = "Alexandria"
    GIZA = "Giza"


# ---------------------------------------------------------------------------
# Pydantic Model
# ---------------------------------------------------------------------------


class Attraction(BaseModel):
    """A single Egyptian heritage site with rich descriptive metadata."""

    name: str = Field(..., description="Official attraction name")
    city: City = Field(..., description="City where the attraction is located")
    maps_url: str = Field(..., description="Google Maps direct link")
    description: str = Field(..., description="Short description (1-2 sentences)")
    type: AttractionType = Field(..., description="Heritage category")
    popularity: int = Field(..., ge=1, le=10, description="Popularity score 1-10")

    # ── Phase 2.4 additions ─────────────────────
    era: str = Field(default="", description="Historical era (e.g. 'Old Kingdom', 'Islamic')")
    description_prompt: str = Field(
        default="",
        description="Prompt template for Gemini-generated rich descriptions",
    )
    coordinates: tuple[float, float] | None = Field(
        default=None, description="GPS (latitude, longitude)"
    )
    class_names: list[str] = Field(
        default_factory=list,
        description="ML classifier labels that map to this attraction",
    )

    # Rich content fields
    highlights: str = Field(..., description="Detailed highlights paragraph")
    visiting_tips: str = Field(..., description="Practical visitor advice")
    historical_significance: str = Field(..., description="Historical context and importance")

    # Optional type-specific metadata
    period: str | None = Field(None, description="Historical period (Pharaonic sites)")
    dynasty: str | None = Field(None, description="Dynasty (Pharaonic sites)")
    notable_pharaohs: list[str] | None = Field(None, description="Associated pharaohs")
    notable_tombs: list[str] | None = Field(None, description="Notable tombs (Valley of Kings)")
    notable_features: list[str] | None = Field(None, description="Key features (bazaars, parks)")
    key_artifacts: list[str] | None = Field(None, description="Key artifacts (museums)")
    architectural_features: list[str] | None = Field(None, description="Architecture highlights")


# ---------------------------------------------------------------------------
# Dataset — 20 curated Egyptian heritage sites
# ---------------------------------------------------------------------------

ATTRACTIONS: list[Attraction] = [
    # ── Cairo ──────────────────────────────────────────────────────────────
    Attraction(
        name="Egyptian Museum",
        city=City.CAIRO,
        maps_url="https://www.google.com/maps/search/?api=1&query=Egyptian+Museum+Cairo",
        description=(
            "Home to the world's largest collection of Pharaonic antiquities, "
            "including treasures from Tutankhamun's tomb."
        ),
        type=AttractionType.PHARAONIC,
        popularity=9,
        era="Modern (houses Pharaonic artifacts)",
        description_prompt="Describe the Egyptian Museum in Cairo, its Pharaonic collection and Tutankhamun treasures.",
        coordinates=(30.0478, 31.2336),
        class_names=["Egyptian_Museum_(Cairo)"],
        key_artifacts=[
            "Tutankhamun's Death Mask",
            "Royal Mummies Collection",
            "Narmer Palette",
            "Statue of Khufu",
        ],
        highlights=(
            "The museum houses over 120,000 artifacts, with the star attraction being "
            "King Tutankhamun's golden mask. Visitors can also explore the Royal Mummies "
            "Hall featuring perfectly preserved remains of Egypt's most powerful pharaohs."
        ),
        visiting_tips=(
            "Visit early in the morning to avoid crowds. Plan at least 3 hours to see "
            "the main highlights. Photography is allowed in most areas but requires a "
            "special ticket."
        ),
        historical_significance=(
            "Founded in 1902, the museum preserves Egypt's ancient heritage and provides "
            "invaluable insights into one of the world's earliest civilizations."
        ),
    ),
    Attraction(
        name="Khan el-Khalili",
        city=City.CAIRO,
        maps_url="https://www.google.com/maps/search/?api=1&query=Khan+el-Khalili+Cairo",
        description=(
            "Historic souk and bazaar dating to the 14th century, famous for traditional "
            "crafts, spices, and Egyptian souvenirs."
        ),
        type=AttractionType.ISLAMIC,
        popularity=8,
        era="Islamic (Mamluk)",
        description_prompt="Describe Khan el-Khalili bazaar in Cairo, its 14th-century history and vibrant market culture.",
        coordinates=(30.0477, 31.2625),
        class_names=["Khan Elkhalili"],
        notable_features=[
            "El-Fishawi Café",
            "Gold District",
            "Spice Market",
            "El-Hussein Mosque",
        ],
        highlights=(
            "This bustling medieval-style marketplace offers a sensory journey through "
            "narrow alleyways filled with shops selling everything from hand-crafted "
            "jewelry and copper goods to textiles, spices, and perfumes."
        ),
        visiting_tips=(
            "Best experienced in late afternoon and evening. Bargaining is expected. "
            "Visit El-Fishawi café, Cairo's oldest café, for traditional Egyptian tea."
        ),
        historical_significance=(
            "Established in 1382 as a caravanserai for traveling merchants, it remains "
            "the commercial heart of historic Cairo."
        ),
    ),
    Attraction(
        name="Al-Azhar Park",
        city=City.CAIRO,
        maps_url="https://www.google.com/maps/search/?api=1&query=Al-Azhar+Park+Cairo",
        description=(
            "A beautiful Islamic garden offering panoramic views of historic Cairo, "
            "featuring Islamic architectural elements."
        ),
        type=AttractionType.ISLAMIC,
        popularity=7,
        era="Modern",
        description_prompt="Describe Al-Azhar Park in Cairo, its Islamic garden design and panoramic city views.",
        coordinates=(30.0393, 31.2661),
        class_names=["Al-Azhar_Park_(Cairo)"],
        notable_features=[
            "Lakeside Café",
            "Citadel View Restaurant",
            "Islamic-Style Gardens",
            "Historic Views",
        ],
        highlights=(
            "This 30-hectare urban oasis provides a peaceful escape from Cairo's bustle "
            "with formal gardens, fountains, and stunning views of the Citadel and "
            "historic Cairo skyline."
        ),
        visiting_tips=(
            "Visit in late afternoon to enjoy sunset views over the city. The park has "
            "excellent restaurants offering both Egyptian and international cuisine."
        ),
        historical_significance=(
            "Built on what was once a 500-year-old garbage dump, this transformation "
            "project was funded by the Aga Khan Trust for Culture and has revitalized "
            "the surrounding historic district."
        ),
    ),
    Attraction(
        name="Ibn Tulun Mosque",
        city=City.CAIRO,
        maps_url="https://www.google.com/maps/search/?api=1&query=Ibn+Tulun+Mosque+Cairo",
        description=(
            "One of the oldest and largest mosques in Egypt with a unique spiral minaret "
            "and vast courtyard."
        ),
        type=AttractionType.ISLAMIC,
        popularity=7,
        era="Islamic (Abbasid)",
        description_prompt="Describe the Mosque of Ibn Tulun in Cairo, its 9th-century spiral minaret and architecture.",
        coordinates=(30.0286, 31.2494),
        class_names=["Ibn Tulun Mosque"],
        architectural_features=[
            "Spiral Minaret",
            "Vast Courtyard",
            "Stucco Decorations",
            "Gypsum Windows",
        ],
        highlights=(
            "This 9th-century architectural masterpiece features a unique spiral minaret "
            "and an expansive open courtyard surrounded by elegant arcades with "
            "distinctive pointed arches."
        ),
        visiting_tips=(
            "Visit in the morning light for the best photography. Dress modestly and "
            "remove shoes before entering the prayer hall. Climb the minaret for "
            "panoramic views of Cairo."
        ),
        historical_significance=(
            "Built in 879 AD, it's the oldest mosque in Egypt that preserves its "
            "original form and one of the largest mosques in the world by land area."
        ),
    ),
    # ── Luxor ──────────────────────────────────────────────────────────────
    Attraction(
        name="Karnak Temple",
        era="New Kingdom",
        description_prompt="Describe the Karnak Temple complex in Luxor, its Great Hypostyle Hall and ancient Egyptian worship.",
        coordinates=(25.7188, 32.6573),
        class_names=[
            "Karnak_precinct_of_Amun-Ra",
            "Great Hypostyle Hall of Karnak",
            "Temple_of_Khonsu_in_Karnak",
        ],
        city=City.LUXOR,
        maps_url="https://www.google.com/maps/search/?api=1&query=Karnak+Temple+Luxor",
        description=(
            "A vast temple complex dedicated to the Theban triad of Amun, Mut, and "
            "Khonsu, featuring massive columns and obelisks."
        ),
        type=AttractionType.PHARAONIC,
        popularity=9,
        period="New Kingdom to Ptolemaic",
        notable_features=[
            "Great Hypostyle Hall",
            "Sacred Lake",
            "Avenue of Sphinxes",
            "Obelisks of Hatshepsut",
        ],
        highlights=(
            "The temple's Great Hypostyle Hall contains 134 massive columns arranged "
            "in 16 rows, creating a forest of stone pillars that once supported a "
            "now-vanished roof. Many columns are over 10 meters tall and covered with "
            "intricate hieroglyphic carvings."
        ),
        visiting_tips=(
            "Visit early morning or late afternoon to avoid the midday heat. Hire a "
            "knowledgeable guide to understand the complex's rich history. The Sound "
            "and Light show in the evening offers a different perspective."
        ),
        historical_significance=(
            "Built over 2,000 years by successive pharaohs, it's the largest religious "
            "building ever constructed and was ancient Egypt's most important place of "
            "worship."
        ),
    ),
    Attraction(
        name="Valley of the Kings",
        era="New Kingdom",
        description_prompt="Describe the Valley of the Kings in Luxor, the royal tombs and their significance.",
        coordinates=(25.7402, 32.6014),
        class_names=[
            "Theban_Necropolis",
            "Tomb_of_Nefertari",
            "Valley_of_the_Queens",
            "KV17",
            "Tomb_of_Nakht_TT52",
        ],
        city=City.LUXOR,
        maps_url="https://www.google.com/maps/search/?api=1&query=Valley+of+the+Kings+Luxor",
        description=(
            "Royal burial ground containing tombs of pharaohs from the New Kingdom, "
            "including Tutankhamun."
        ),
        type=AttractionType.PHARAONIC,
        popularity=9,
        period="New Kingdom",
        notable_tombs=[
            "KV62 (Tutankhamun)",
            "KV17 (Seti I)",
            "KV7 (Ramses II)",
            "KV5 (Sons of Ramses II)",
        ],
        highlights=(
            "This desert valley contains 63 magnificent royal tombs carved deep into "
            "the rock, with walls covered in vivid paintings depicting Egyptian "
            "mythology and the pharaoh's journey to the afterlife."
        ),
        visiting_tips=(
            "Standard tickets include access to three tombs of your choice. Special "
            "tickets are required for premium tombs like Tutankhamun's. No photography "
            "is allowed inside the tombs. Visit early in the morning when temperatures "
            "are cooler."
        ),
        historical_significance=(
            "For nearly 500 years (16th to 11th century BC), this secluded valley "
            "served as the burial place for most of Egypt's New Kingdom rulers, marking "
            "a shift from the earlier pyramid tombs."
        ),
    ),
    Attraction(
        name="Luxor Temple",
        era="New Kingdom",
        description_prompt="Describe Luxor Temple, its colossal statues and role in ancient Egyptian festivals.",
        coordinates=(25.6995, 32.6390),
        class_names=["Luxor_Temple"],
        city=City.LUXOR,
        maps_url="https://www.google.com/maps/search/?api=1&query=Luxor+Temple+Luxor",
        description=(
            "Ancient Egyptian temple complex located on the east bank of the Nile "
            "River, known for its colossal statues and beautiful colonnades."
        ),
        type=AttractionType.PHARAONIC,
        popularity=8,
        period="New Kingdom",
        notable_pharaohs=["Amenhotep III", "Ramses II"],
        highlights=(
            "Unlike other temples dedicated to gods, Luxor Temple was dedicated to the "
            "rejuvenation of kingship. It features a 25-meter tall pink granite obelisk "
            "(whose twin now stands in Paris), massive seated statues of Ramses II, and "
            "beautiful colonnaded courtyards."
        ),
        visiting_tips=(
            "Visit at night when the temple is dramatically illuminated. The temple is "
            "centrally located in Luxor city and easily accessible on foot from many "
            "hotels."
        ),
        historical_significance=(
            "Connected to Karnak Temple by the Avenue of Sphinxes, this temple was "
            "where many pharaohs were crowned, including potentially Alexander the Great."
        ),
    ),
    Attraction(
        name="Temple of Hatshepsut",
        era="New Kingdom",
        description_prompt="Describe the Mortuary Temple of Hatshepsut at Deir el-Bahari and the story of Egypt's female pharaoh.",
        coordinates=(25.7381, 32.6075),
        class_names=["Deir_el-Bahari", "Hatshepsut Temple", "Hatshepsut face", "Hatshepsut Statue"],
        city=City.LUXOR,
        maps_url="https://www.google.com/maps/search/?api=1&query=Temple+of+Hatshepsut+Luxor",
        description=(
            "Mortuary temple of the female pharaoh Hatshepsut, featuring terraced "
            "colonnades set against dramatic cliffs."
        ),
        type=AttractionType.PHARAONIC,
        popularity=8,
        period="New Kingdom",
        dynasty="18th Dynasty",
        highlights=(
            "This unique temple features three dramatic ascending terraces with "
            "colonnaded facades, set dramatically against the sheer cliffs of Deir "
            "el-Bahari. Relief sculptures depict the divine birth of Hatshepsut and "
            "her famous trading expedition to the land of Punt."
        ),
        visiting_tips=(
            "Visit early morning for the best lighting and views. The site has limited "
            "shade, so bring sunscreen and water. A short electric train connects the "
            "parking area to the temple entrance."
        ),
        historical_significance=(
            "Built for one of Egypt's few female pharaohs who ruled for 20 years as "
            "king. After her death, her successor Thutmose III attempted to erase her "
            "legacy by destroying her images."
        ),
    ),
    # ── Aswan ──────────────────────────────────────────────────────────────
    Attraction(
        name="Abu Simbel",
        era="New Kingdom",
        description_prompt="Describe the Abu Simbel temples built by Ramesses II and the 1960s UNESCO relocation project.",
        coordinates=(22.3370, 31.6256),
        class_names=["The Great Temple of Ramesses II", "Colossal Statue of Ramesses II"],
        city=City.ASWAN,
        maps_url="https://www.google.com/maps/search/?api=1&query=Abu+Simbel+Aswan",
        description=(
            "Massive rock temples built by Ramses II, featuring colossal statues and "
            "intricate carvings."
        ),
        type=AttractionType.PHARAONIC,
        popularity=9,
        period="New Kingdom",
        dynasty="19th Dynasty",
        highlights=(
            "Two massive rock temples with four 20-meter high seated statues of "
            "Ramses II guarding the entrance. Twice a year (February 22 and October 22), "
            "the sun penetrates the main temple to illuminate the innermost sanctuary "
            "statues."
        ),
        visiting_tips=(
            "Most visitors arrive on day trips from Aswan by plane or convoy. Visit "
            "early morning to avoid crowds and heat. The Sound and Light show in the "
            "evening is spectacular."
        ),
        historical_significance=(
            "In the 1960s, both temples were completely dismantled and relocated 65 "
            "meters higher to save them from submersion when the Aswan High Dam created "
            "Lake Nasser - one of the greatest archaeological rescue operations in "
            "history."
        ),
    ),
    Attraction(
        name="Philae Temple",
        era="Ptolemaic",
        description_prompt="Describe the Temple of Isis at Philae island in Aswan and its Greco-Roman architecture.",
        coordinates=(24.0244, 32.8842),
        class_names=["Temple_of_Isis_in_Philae", "Kiosk_of_Trajan_in_Philae"],
        city=City.ASWAN,
        maps_url="https://www.google.com/maps/search/?api=1&query=Philae+Temple+Aswan",
        description=(
            "Island temple complex dedicated to the goddess Isis, rescued from the "
            "rising waters of Lake Nasser after the Aswan Dam."
        ),
        type=AttractionType.PHARAONIC,
        popularity=8,
        period="Ptolemaic to Roman",
        highlights=(
            "Set on a picturesque island, this beautiful temple complex combines "
            "Egyptian and Greco-Roman architectural elements. The main temple is "
            "dedicated to Isis, sister-wife of Osiris and mother of Horus."
        ),
        visiting_tips=(
            "Accessible only by boat, which adds to the experience. The Sound and "
            "Light show is among Egypt's best. Morning visits offer better lighting "
            "for photography."
        ),
        historical_significance=(
            "This was the last active temple of the ancient Egyptian religion, with "
            "hieroglyphics still being added in the 5th century AD. The temple was "
            "completely dismantled and relocated when the Aswan Dam was built."
        ),
    ),
    Attraction(
        name="The Unfinished Obelisk",
        era="New Kingdom",
        description_prompt="Describe the Unfinished Obelisk in Aswan's granite quarries and ancient Egyptian stone-working techniques.",
        coordinates=(24.0750, 32.8942),
        class_names=["Unfinished_obelisk_in_Aswan"],
        city=City.ASWAN,
        maps_url="https://www.google.com/maps/search/?api=1&query=The+Unfinished+Obelisk+Aswan",
        description=(
            "Enormous obelisk abandoned in the quarry when cracks appeared, providing "
            "insights into ancient stoneworking techniques."
        ),
        type=AttractionType.PHARAONIC,
        popularity=7,
        period="New Kingdom",
        highlights=(
            "This massive unfinished obelisk would have been the largest ever erected "
            "at 42 meters tall and weighing 1,200 tons. Its partial carving offers "
            "unique insights into ancient Egyptian stone quarrying and carving techniques."
        ),
        visiting_tips=(
            "Visit in the morning when temperatures are cooler. A knowledgeable guide "
            "can explain the ancient quarrying techniques visible at the site."
        ),
        historical_significance=(
            "Likely commissioned by Queen Hatshepsut, it was abandoned when cracks "
            "appeared during carving. It demonstrates the incredible stone-working "
            "skills of ancient Egyptians without modern technology."
        ),
    ),
    Attraction(
        name="Elephantine Island",
        era="Ancient (multi-period)",
        description_prompt="Describe Elephantine Island in Aswan, its Nilometer and the Temple of Khnum ruins.",
        coordinates=(24.0854, 32.8870),
        class_names=["Kitchener's_Island", "Aswan_Botanical_Garden"],
        city=City.ASWAN,
        maps_url="https://www.google.com/maps/search/?api=1&query=Elephantine+Island+Aswan",
        description=(
            "Island with ruins of the Temple of Khnum and a nilometer used to measure "
            "the Nile flood levels."
        ),
        type=AttractionType.PHARAONIC,
        popularity=6,
        period="Multiple periods",
        highlights=(
            "This peaceful island in the middle of the Nile features ancient temple "
            "ruins, a museum with artifacts spanning 5,000 years, and one of the oldest "
            "nilometers used to measure the critical Nile floods."
        ),
        visiting_tips=(
            "Easily reached by local ferry or felucca. The Aswan Museum displays "
            "artifacts from the island. The Nubian villages on the southern end offer "
            "cultural experiences and colorful architecture."
        ),
        historical_significance=(
            "Served as Egypt's southern frontier for much of its history, with "
            "strategic and economic importance as the gateway to Nubia and Africa. "
            "Archaeological evidence shows continuous settlement since the Predynastic "
            "period."
        ),
    ),
    # ── Alexandria ─────────────────────────────────────────────────────────
    Attraction(
        name="Bibliotheca Alexandrina",
        era="Modern",
        description_prompt="Describe the Bibliotheca Alexandrina, the modern revival of the ancient Library of Alexandria.",
        coordinates=(31.2089, 29.9092),
        class_names=["Bibliotheca_Alexandrina", "Bibliotheca_Alexandrina_planetarium"],
        city=City.ALEXANDRIA,
        maps_url="https://www.google.com/maps/search/?api=1&query=Bibliotheca+Alexandrina+Alexandria",
        description=(
            "Modern library and cultural center built to recapture the spirit of the "
            "ancient Library of Alexandria."
        ),
        type=AttractionType.MODERN,
        popularity=8,
        highlights=(
            "This striking modern architectural marvel houses multiple libraries, four "
            "museums, a planetarium, and numerous art galleries and exhibition spaces. "
            "The main reading room can accommodate 2,000 readers under its sloping "
            "glass roof."
        ),
        visiting_tips=(
            "Join a guided tour to fully appreciate the architecture and facilities. "
            "The Antiquities Museum and Manuscript Museum inside are worth visiting. "
            "Check the website for cultural events and exhibitions."
        ),
        historical_significance=(
            "Built as a memorial to the ancient Library of Alexandria, once the largest "
            "in the world and center of learning in the ancient world until its "
            "destruction in antiquity."
        ),
    ),
    Attraction(
        name="Citadel of Qaitbay",
        era="Islamic (Mamluk)",
        description_prompt="Describe the Citadel of Qaitbay in Alexandria, built on the site of the ancient Pharos lighthouse.",
        coordinates=(31.2139, 29.8856),
        class_names=["Qaitbay Castle", "Citadel_of_Qaitbay"],
        city=City.ALEXANDRIA,
        maps_url="https://www.google.com/maps/search/?api=1&query=Citadel+of+Qaitbay+Alexandria",
        description=(
            "15th-century defensive fortress built on the site of the ancient "
            "Lighthouse of Alexandria."
        ),
        type=AttractionType.ISLAMIC,
        popularity=8,
        highlights=(
            "This picturesque medieval fortress features thick walls, winding passages, "
            "and panoramic views of the Mediterranean. Built with stones from the "
            "collapsed Lighthouse of Alexandria, one of the Seven Wonders of the "
            "Ancient World."
        ),
        visiting_tips=(
            "Visit late afternoon for beautiful sunset views over the Mediterranean. "
            "Wear comfortable shoes as there are many stairs to climb. The Naval Museum "
            "inside has modest displays but interesting artifacts."
        ),
        historical_significance=(
            "Built in 1477 by Sultan Qaitbay on the exact site of the famous Lighthouse "
            "of Alexandria (Pharos), which had collapsed after an earthquake. It served "
            "as an important defensive stronghold against Ottoman attacks."
        ),
    ),
    Attraction(
        name="Catacombs of Kom El Shoqafa",
        era="Greco-Roman",
        description_prompt="Describe the Catacombs of Kom el Shoqafa in Alexandria, a blend of Egyptian and Roman funerary art.",
        coordinates=(31.1792, 29.8947),
        class_names=["Kom_el-Shoqafa"],
        city=City.ALEXANDRIA,
        maps_url="https://www.google.com/maps/search/?api=1&query=Catacombs+of+Kom+El+Shoqafa+Alexandria",
        description=(
            "Vast Roman-era underground necropolis combining Egyptian, Greek, and "
            "Roman artistic elements."
        ),
        type=AttractionType.GRECO_ROMAN,
        popularity=7,
        highlights=(
            "These three-level underground tomb complexes feature a unique blend of "
            "Pharaonic, Greek and Roman artistic elements. The main tomb chamber has "
            "sculptures showing Egyptian gods in Roman dress, demonstrating the "
            "cultural fusion of the time."
        ),
        visiting_tips=(
            "Bring a sweater as it can be cool underground. The site requires some "
            "stair climbing. Photography is permitted but without flash."
        ),
        historical_significance=(
            "Dating from the 2nd century AD, these are considered one of the Seven "
            "Wonders of the Middle Ages. They demonstrate the multicultural nature of "
            "Roman Alexandria with their fusion of artistic styles."
        ),
    ),
    Attraction(
        name="Montazah Palace Gardens",
        era="Modern",
        description_prompt="Describe the Montazah Palace Gardens in Alexandria, the royal seaside estate and its botanical gardens.",
        coordinates=(31.2870, 30.0172),
        class_names=["Montaza_Palace"],
        city=City.ALEXANDRIA,
        maps_url="https://www.google.com/maps/search/?api=1&query=Montazah+Palace+Gardens+Alexandria",
        description=(
            "Extensive royal gardens surrounding the Montazah Palace with beaches, "
            "woods, and formal gardens."
        ),
        type=AttractionType.MODERN,
        popularity=7,
        highlights=(
            "This 150-acre royal park features beautiful landscaped gardens, palm-lined "
            "avenues, and the distinctive Montazah Palace with its blend of Turkish and "
            "Florentine architectural styles. The park includes private beaches and woods."
        ),
        visiting_tips=(
            "A perfect escape from Alexandria's urban bustle. While the palace itself is "
            "not open to the public, the gardens and beaches are accessible with an "
            "entrance ticket. Bring a picnic and swimwear in summer."
        ),
        historical_significance=(
            "Built by Khedive Abbas II, the last Muhammad Ali Dynasty ruler, in 1892 "
            "as a summer residence for the Egyptian royal family. After the 1952 "
            "revolution, it became a presidential palace."
        ),
    ),
    # ── Giza ───────────────────────────────────────────────────────────────
    Attraction(
        name="Great Pyramids of Giza",
        city=City.GIZA,
        maps_url="https://www.google.com/maps/search/?api=1&query=Great+Pyramids+of+Giza+Giza",
        description=(
            "The last remaining wonder of the ancient world, massive structures built "
            "as tombs for the pharaohs."
        ),
        type=AttractionType.PHARAONIC,
        popularity=10,
        era="Old Kingdom",
        description_prompt="Describe the Great Pyramids of Giza, the last wonder of the ancient world and their construction.",
        coordinates=(29.9792, 31.1342),
        class_names=[
            "Great Pyramids of Giza",
            "Bent_Pyramid",
            "Red_Pyramid",
            "Pyramid_of_Djoser",
            "Pyramid_of_Unas",
            "Pyramid_of_Sahure",
        ],
        period="Old Kingdom",
        dynasty="4th Dynasty",
        notable_pharaohs=["Khufu", "Khafre", "Menkaure"],
        highlights=(
            "The Great Pyramid of Khufu stands 147 meters tall and contains over 2.3 "
            "million stone blocks weighing 2.5-15 tons each. The precision of "
            "construction is remarkable - the base is level to within 2.1 cm, and the "
            "sides are aligned to the cardinal directions with an accuracy of up to "
            "0.05 degrees."
        ),
        visiting_tips=(
            "Arrive early morning or late afternoon to avoid crowds and midday heat. "
            "Entrance tickets to the pyramid interiors are limited and sold separately. "
            "Camel and horse rides are negotiable but agree on price beforehand."
        ),
        historical_significance=(
            "Built around 2560 BC, the Great Pyramid remained the tallest human-made "
            "structure in the world for nearly 4,000 years. The complex demonstrates "
            "the Egyptians' advanced knowledge of mathematics, astronomy, and "
            "engineering."
        ),
    ),
    Attraction(
        name="Great Sphinx of Giza",
        city=City.GIZA,
        maps_url="https://www.google.com/maps/search/?api=1&query=Great+Sphinx+of+Giza+Giza",
        description=(
            "Massive limestone statue with the body of a lion and the head of a human, "
            "thought to represent King Khafre."
        ),
        type=AttractionType.PHARAONIC,
        popularity=9,
        era="Old Kingdom",
        description_prompt="Describe the Great Sphinx of Giza, the enigmatic limestone colossus guarding the pyramids.",
        coordinates=(29.9753, 31.1376),
        class_names=["Great_Sphinx_of_Giza", "Sphinx_of_Memphis"],
        period="Old Kingdom",
        dynasty="4th Dynasty",
        highlights=(
            "This enigmatic monument stands 20 meters tall and 73 meters long, making "
            "it the largest monolithic statue in the world. Carved from a single ridge "
            "of limestone, it has captured human imagination for thousands of years."
        ),
        visiting_tips=(
            "Visit early morning or close to sunset for dramatic lighting and "
            "photographs. The Sphinx is viewed from a viewing platform at its base - "
            "you cannot touch or climb it."
        ),
        historical_significance=(
            "Shrouded in mystery regarding its exact purpose and construction date. "
            "Between its paws stands the Dream Stela, placed by Thutmose IV, telling "
            "how the Sphinx appeared in his dream promising kingship if he cleared the "
            "sand covering it."
        ),
    ),
    Attraction(
        name="Pyramids of Giza Sound and Light Show",
        city=City.GIZA,
        maps_url="https://www.google.com/maps/search/?api=1&query=Pyramids+of+Giza+Sound+and+Light+Show+Giza",
        description=(
            "Nighttime spectacle that brings ancient history to life through dramatic "
            "narration, music, and illumination of the pyramids and Sphinx."
        ),
        type=AttractionType.PHARAONIC,
        popularity=8,
        era="Modern",
        description_prompt="Describe the Pyramids of Giza Sound and Light Show and its dramatic retelling of ancient history.",
        coordinates=(29.9753, 31.1376),
        class_names=[],
        highlights=(
            "This evening show uses dramatic lighting effects, music, and narration to "
            "tell the story of ancient Egypt. The pyramids and Sphinx are illuminated "
            "in changing colors while the voice of the Sphinx recounts 5,000 years of "
            "Egyptian history."
        ),
        visiting_tips=(
            "Shows are presented in different languages on different nights - check the "
            "schedule. Booking in advance is recommended in high season. Bring a jacket "
            "as desert evenings can be cool."
        ),
        historical_significance=(
            "Though a modern attraction, the show helps visitors connect with the "
            "ancient history and mythology surrounding these monuments, using advanced "
            "technology to tell ancient stories."
        ),
    ),
    Attraction(
        name="Tomb of Meresankh III",
        city=City.GIZA,
        maps_url="https://www.google.com/maps/search/?api=1&query=Tomb+of+Meresankh+III+Giza",
        description=(
            "Exceptionally well-preserved tomb of a queen from the 4th Dynasty with "
            "vivid colors and statues."
        ),
        type=AttractionType.PHARAONIC,
        popularity=7,
        era="Old Kingdom",
        description_prompt="Describe the Tomb of Meresankh III in Giza, its vivid reliefs and insight into royal women's lives.",
        coordinates=(29.9797, 31.1319),
        class_names=[],
        period="Old Kingdom",
        dynasty="4th Dynasty",
        highlights=(
            "This hidden gem features remarkably preserved colorful reliefs and ten "
            "life-sized statues of women carved from the living rock. The burial "
            "chamber walls retain their vibrant original colors after more than "
            "4,500 years."
        ),
        visiting_tips=(
            "Located in the Eastern Cemetery near the Great Pyramid. Less visited than "
            "other attractions, offering a more intimate experience. A special ticket "
            "may be required as it's often opened on rotation with other tombs."
        ),
        historical_significance=(
            "Meresankh III was the granddaughter of King Khufu and wife of King Khafre. "
            "Her tomb provides rare insights into the lives of royal women in the Old "
            "Kingdom and features some of the best-preserved Old Kingdom paintings."
        ),
    ),
]


# ---------------------------------------------------------------------------
# Fallback sentiment scores (for when Reddit API is unavailable)
# ---------------------------------------------------------------------------

FALLBACK_SENTIMENT_SCORES: dict[str, float] = {
    "pyramids": 8.5,
    "egyptian museum": 8.2,
    "karnak temple": 8.8,
    "valley of the kings": 8.6,
    "abu simbel": 9.1,
    "khan el-khalili": 7.8,
    "alexandria": 7.9,
    "aswan": 8.3,
    "luxor": 8.7,
    "cairo": 7.5,
}


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

# Pre-built index: ML class label → Attraction (O(1) lookup)
_CLASS_NAME_INDEX: dict[str, Attraction] = {}
for _attr in ATTRACTIONS:
    for _cn in _attr.class_names:
        _CLASS_NAME_INDEX[_cn.lower()] = _attr


def _slugify(name: str) -> str:
    """Convert an attraction name to a URL-safe slug.

    Example: ``"Great Pyramids of Giza"`` → ``"great-pyramids-of-giza"``.
    """
    import re

    slug = name.lower().strip()
    slug = re.sub(r"[''`]", "", slug)  # Remove apostrophes
    slug = re.sub(r"[^a-z0-9]+", "-", slug)  # Non-alphanumeric → dash
    return slug.strip("-")


# Pre-built index: slug → Attraction (O(1) lookup)
_SLUG_INDEX: dict[str, Attraction] = {_slugify(a.name): a for a in ATTRACTIONS}


def get_all() -> list[Attraction]:
    """Return all attractions."""
    return ATTRACTIONS


def get_by_slug(slug: str) -> Attraction | None:
    """Find an attraction by its URL slug (case-insensitive).

    Slugs are derived from attraction names:
    ``"Great Pyramids of Giza"`` → ``"great-pyramids-of-giza"``.

    Args:
        slug: URL-safe slug string.

    Returns:
        The matching ``Attraction`` or ``None``.
    """
    return _SLUG_INDEX.get(slug.lower().strip())


def get_slug(attraction: Attraction) -> str:
    """Return the URL slug for the given attraction."""
    return _slugify(attraction.name)


def get_by_name(name: str) -> Attraction | None:
    """Find an attraction by exact name (case-insensitive)."""
    name_lower = name.lower()
    return next((a for a in ATTRACTIONS if a.name.lower() == name_lower), None)


def get_by_class_name(class_name: str) -> Attraction | None:
    """Map an ML classifier label to a curated attraction.

    This bridges the 175-class Keras model output to the 20 curated
    attraction records.  If the class name doesn't map to any known
    attraction, ``None`` is returned.

    Args:
        class_name: A label from the classifier (e.g. ``"Great Pyramids of Giza"``).

    Returns:
        The matching ``Attraction`` or ``None``.
    """
    return _CLASS_NAME_INDEX.get(class_name.lower())


def get_by_category(
    *,
    attraction_type: AttractionType | str | None = None,
    era: str | None = None,
) -> list[Attraction]:
    """Filter attractions by type and/or era.

    Args:
        attraction_type: Heritage category (e.g. ``"Pharaonic"``).
        era: Historical era substring (e.g. ``"New Kingdom"``).

    Returns:
        List of matching attractions (both filters are AND-ed).
    """
    results = list(ATTRACTIONS)

    if attraction_type is not None:
        type_value = (
            attraction_type.value
            if isinstance(attraction_type, AttractionType)
            else attraction_type
        )
        type_lower = type_value.lower()
        results = [a for a in results if a.type.value.lower() == type_lower]

    if era is not None:
        era_lower = era.lower()
        results = [a for a in results if era_lower in a.era.lower()]

    return results


def get_by_city(city: City | str) -> list[Attraction]:
    """Return all attractions in a given city."""
    city_value = city.value if isinstance(city, City) else city
    return [a for a in ATTRACTIONS if a.city.value == city_value]


def get_by_type(attraction_type: AttractionType | str) -> list[Attraction]:
    """Return all attractions of a given heritage type."""
    type_value = (
        attraction_type.value if isinstance(attraction_type, AttractionType) else attraction_type
    )
    return [a for a in ATTRACTIONS if a.type.value == type_value]


def search(query: str) -> list[Attraction]:
    """Simple keyword search across name, description, highlights, and era."""
    q = query.lower()
    results: list[Attraction] = []
    for a in ATTRACTIONS:
        if (
            q in a.name.lower()
            or q in a.description.lower()
            or q in a.highlights.lower()
            or q in a.city.value.lower()
            or q in a.type.value.lower()
            or q in a.era.lower()
        ):
            results.append(a)
    return results


def get_top_rated(n: int = 5) -> list[Attraction]:
    """Return the top-N attractions sorted by popularity descending."""
    return sorted(ATTRACTIONS, key=lambda a: a.popularity, reverse=True)[:n]


def get_sentiment_score(keyword: str) -> float | None:
    """Look up a fallback sentiment score for a keyword."""
    return FALLBACK_SENTIMENT_SCORES.get(keyword.lower())
