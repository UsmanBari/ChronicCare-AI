#!/usr/bin/env python3
"""
scripts/eval/gen_red_flag_corpus.py
Generates a systematic held-out evaluation corpus for Stage-1 Red Flag detection (Part R5).

Cross-product of:
- Subjects (self, family members, caregiver pronouns)
- Core symptom families (chest_pressure, breathing_failure, face_droop, speech_failure,
  limb_failure, unresponsive, intractable_vomiting)
- Qualifiers (acute onset, severity, duration)
- Spelling variants (Roman Urdu aa/a, ee/i, me/mein, nhi/nahi, rha/raha, etc.)
- Tense and respect verb forms (raha hai, rahe hain, rahi hain, ho gaya, etc.)
- 3 Languages: English (en), Roman Urdu (ur-Latn), Urdu script (ur).

Negatives are built systematically using:
- Preceding negation frames
- Trailing negation frames
- Echo-question and short-answer negations (R5.3)
- Remote-past resolved history
- Benign activity/postural numbness
- Benign food-triggered heartburn
- Bare negative answers
- Routine normal check-in statements

Fixes random seed (42) and writes >= 600 positives and >= 600 negatives to:
tests/fixtures/red_flag_heldout_r5.json
"""

import json
import random
from pathlib import Path


def generate_corpus(seed: int = 42, num_positives: int = 700, num_negatives: int = 700):
    random.seed(seed)

    # =========================================================================
    # 1. POSITIVES GENERATOR
    # =========================================================================

    # Categories to generate
    # chest_pain, breathing, confusion_and_stroke, loss_of_consciousness, dka_vomiting_high_glucose

    en_pos_templates = {
        "chest_pain": [
            "{subj} experiencing crushing chest pressure right now",
            "{subj} having severe squeezing pain in the center of the chest",
            "{subj} feeling heavy weight like an elephant sitting on chest",
            "{subj} sudden onset of severe chest tightness spreading to left arm",
            "{subj} acute chest pressure with cold sweating and nausea",
            "{subj} vice-like crushing pain in chest since 20 minutes",
            "{subj} band of heavy pressure around chest, worsening rapidly",
            "{subj} intense heavy chest ache, unbearable and agonizing",
        ],
        "breathing": [
            "{subj} completely unable to breathe and choking right now",
            "{subj} gasping desperately for air while sitting completely still",
            "{subj} sudden severe breathlessness and lips are turning blue",
            "{subj} suffocating feeling, cannot get any air into the lungs",
            "{subj} struggling to breathe with severe wheezing and gasping",
            "{subj} acute respiratory distress, choking and panting heavily",
            "{subj} cannot catch breath at all, severe gasping for air",
            "{subj} air won't go in, severe shortness of breath at complete rest",
        ],
        "confusion_and_stroke": [
            "{subj} face has suddenly dropped on one side with crooked smile",
            "{subj} speech became slurred and cannot form words properly",
            "{subj} right arm went completely limp and cannot lift it at all",
            "{subj} facial droop observed and words are jumbled nonsense",
            "{subj} sudden loss of power in left side, dropping the cup",
            "{subj} cannot speak clearly, slurring speech and mouth is lopsided",
            "{subj} unable to move or raise right leg and arm suddenly",
            "{subj} one side of face is sagging and unable to communicate words",
        ],
        "loss_of_consciousness": [
            "{subj} suddenly collapsed to the floor and is totally unconscious",
            "{subj} passed out abruptly and will not wake up",
            "{subj} fainted suddenly and is unresponsive to shaking",
            "{subj} blacked out completely, eyes won't open and no response",
            "{subj} lost consciousness suddenly, lying unresponsive on the ground",
            "{subj} had a syncopal blackout and is out cold right now",
            "{subj} collapsed and unresponsive, not waking up at all",
            "{subj} sudden blackout and passed out on the ground",
        ],
        "dka_vomiting_high_glucose": [
            "{subj} vomiting non-stop for hours and cannot keep water down",
            "{subj} throwing up constantly, unable to hold any fluids or ORS",
            "{subj} persistent severe vomiting every 20 minutes, dehydrating fast",
            "{subj} cannot keep even sips of water in, vomiting continuously",
            "{subj} intractable vomiting since morning, fluids come right back up",
            "{subj} throwing up repeatedly, nothing stays down at all",
            "{subj} vomiting uncontrollably with high blood sugar",
            "{subj} severe constant vomiting, unable to retain any food or liquid",
        ],
    }

    en_subjects = [
        "I am", "My father is", "My mother is", "My grandmother is", "My grandfather is",
        "My husband is", "My wife is", "The patient is", "He is", "She is"
    ]

    ur_latn_pos_templates = {
        "chest_pain": [
            "{subj} seene {prep} shadeed {press} aur dard ho {v_form}",
            "{subj} seenay par bhari bojh aur jakran mehsoos ho {v_form}",
            "{subj} sina par pathar rakha hua lag {v_form} hai, sans ruk rahi hai",
            "{subj} seene {prep} kasav aur dabaao bardasht {neg_verb} ho {v_form}",
            "{subj} seene ka shadeed dabav bazu tak phail {v_form} hai",
            "{subj} jaise koi seene par baitha daba {v_form} ho, dard bohat shadeed hai",
            "{subj} seenay me nichor aur crushing dabav hai",
            "{subj} seene me achanak sakht jakran aur paseena aa {v_form}",
        ],
        "breathing": [
            "{subj} sans bilkul {neg_verb} aa {v_form} aur dam ghut {v_form} hai",
            "{subj} sans phans gayi hai aur hawa andar {neg_verb} ja {v_form}",
            "{subj} achanak sans lena dushwar ho gaya hai, haanp {v_form} hain",
            "{subj} bethay hue bhi sans phool {v_form} hai aur sans ukhad gayi hai",
            "{subj} sans le hi {neg_verb} pa {v_form}, shadeed dam ghutan hai",
            "{subj} haanp {v_form} hain aur hont neelay par gaye hain",
            "{subj} sans atki hui hai aur achanak hawa {neg_verb} mil {v_form}",
            "{subj} sans ukhri hui hai achanak bohat shadeed takleef hai",
        ],
        "confusion_and_stroke": [
            "{subj} chehra ek taraf latak gaya hai aur munh terha ho gaya",
            "{subj} zaban larkhara {v_form} hai aur baat {neg_verb} kar pa {v_form}",
            "{subj} lafz {neg_verb} nikal rahe aur achanak bolna band ho gaya",
            "{subj} bazu bejaan ho gaya hai aur uth {neg_verb} {v_form}",
            "{subj} haath se cup gir jata hai, pakar {neg_verb} pa {v_form}",
            "{subj} chehra dhalak gaya hai aur ulti seedhi baatein kar {v_form}",
            "{subj} ek taraf ka jism sunn aur bekaar ho gaya hai",
            "{subj} munh tedha ho gaya aur awaaz {neg_verb} nikal {v_form}",
        ],
        "loss_of_consciousness": [
            "{subj} achanak behosh ho gaye aur hosh {neg_verb} aa {v_form}",
            "{subj} ghashi kha kar gir pare aur aankhein {neg_verb} khol rahe",
            "{subj} behosh pare hain, hila ke dekha koi jawab {neg_verb} mila",
            "{subj} hosh kho baithe hain aur jag {neg_verb} rahe",
            "{subj} bayhosh ho kar zameen par gir pare",
            "{subj} achanak chakkar kha kar behosh ho gaye, unko hosh {neg_verb}",
            "{subj} bilkul be hosh hain koi harkat {neg_verb} ho {v_form}",
            "{subj} ghashi ka daura para aur bilkul sunn ho gaye",
        ],
        "dka_vomiting_high_glucose": [
            "{subj} har ghante ulti ho {v_form} hai, pani bhi andar {neg_verb} theharta",
            "{subj} musalsal ultiyan aa {v_form} hain, kuch bhi andar {neg_verb} tikta",
            "{subj} subah se ulti ruk hi {neg_verb} rahi, jo peete hain bahar nikal jata hai",
            "{subj} bar bar qay ho {v_form} hai, ORS bhi wapas nikal jata hai",
            "{subj} nonstop ulti ho {v_form} hai aur sugar bohat high hai",
            "{subj} pani ka ghoont bhi {neg_verb} rukta, foran ulti aa jati hai",
            "{subj} lagataar ultiyan ho {v_form} hain kuch hazam {neg_verb} ho {v_form}",
            "{subj} ulti rukne ka naam {neg_verb} le {v_form}, dehydration ho gayi hai",
        ],
    }

    ur_latn_subjects = [
        "mujhe", "ammi ko", "abba ko", "nani ko", "dada ko", "mere shohar ko",
        "meri begum ko", "bachon ke abbu ko", "baba ko", "unko", "use", "woh"
    ]
    ur_latn_preps = ["me", "mein", "main", "mai"]
    ur_latn_press = ["dabao", "dabav", "bojh", "jakran", "pathar", "kasav", "dabaao"]
    ur_latn_neg_verbs = ["nahi", "nhi", "nai", "nahin"]
    ur_latn_v_forms = ["raha", "rahe", "rahi", "rha", "rahay"]

    ur_pos_templates = {
        "chest_pain": [
            "{subj} سینے میں شدید دباؤ اور درد ہو رہا ہے",
            "{subj} سینے پر بھاری بوجھ اور جکڑن محسوس ہو رہی ہے",
            "{subj} سینے پر پتھر رکھا ہوا لگ رہا ہے اور دم گھٹ رہا ہے",
            "{subj} سینے میں شدید کساؤ اور نچوڑ ہے",
            "{subj} سینے کا شدید دباؤ بائیں بازو تک جا رہا ہے",
            "{subj} جیسے کوئی سینے پر بیٹھ کر دبا رہا ہو، درد بے حد ہے",
            "{subj} سینے میں شدید دباؤ اور پسینہ آ رہا ہے",
            "{subj} سینے میں اچانک شدید گھٹن اور جکڑن ہو گئی ہے",
        ],
        "breathing": [
            "{subj} سانس بالکل نہیں آ رہی اور دم گھٹ رہا ہے",
            "{subj} سانس پھنس گئی ہے اور ہوا اندر نہیں جا رہی",
            "{subj} اچانک سانس لینا دشوار ہو گیا ہے اور ہانپ رہے ہیں",
            "{subj} بیٹھے ہوئے بھی سانس پھول رہی ہے اور سانس اکھڑ گئی ہے",
            "{subj} سانس لے ہی نہیں پا رہے، شدید دم گھٹن ہے",
            "{subj} ہانپ رہے ہیں اور ہونٹ نیلے پڑ گئے ہیں",
            "{subj} سانس اٹکی ہوئی ہے اور ہوا نہیں مل رہی",
            "{subj} سانس اکھڑی ہوئی ہے اور بات کرنا محال ہو گیا ہے",
        ],
        "confusion_and_stroke": [
            "{subj} چہرہ ایک طرف لٹک گیا ہے اور منہ ٹیڑھا ہو گیا",
            "{subj} زبان لڑکھڑا رہی ہے اور بات نہیں کر پا رہے",
            "{subj} الفاظ نہیں نکل رہے اور اچانک بولنا بند ہو گیا",
            "{subj} بازو بے جان ہو گیا ہے اور اٹھ نہیں رہا",
            "{subj} ہاتھ سے چیزیں گر رہی ہیں، پکڑ نہیں پا رہے",
            "{subj} چہرہ ڈھلک گیا ہے اور الٹی سیدھی باتیں کر رہے ہیں",
            "{subj} ایک طرف کا جسم سن اور بیکار ہو گیا ہے",
            "{subj} منہ ٹیڑھا ہو گیا اور آواز نہیں نکل رہی",
        ],
        "loss_of_consciousness": [
            "{subj} اچانک بے ہوش ہو گئے اور ہوش نہیں آ رہا",
            "{subj} غشی طاری ہو گئی ہے اور آنکھیں نہیں کھول رہے",
            "{subj} بے ہوش پڑے ہیں، ہلا کر دیکھا کوئی جواب نہیں ملا",
            "{subj} ہوش کھو بیٹھے ہیں اور جاگ نہیں رہے",
            "{subj} بے ہوش ہو کر زمین پر گر پڑے ہیں",
            "{subj} اچانک چکر کھا کر بے ہوش ہو گئے ہیں",
            "{subj} بالکل بے ہوش ہیں کوئی حرکت نہیں ہو رہی",
            "{subj} غشی کا دورہ پڑا اور بالکل بے ہوش ہیں",
        ],
        "dka_vomiting_high_glucose": [
            "{subj} ہر گھنٹے الٹی ہو رہی ہے، پانی بھی اندر نہیں ٹھہر رہا",
            "{subj} مسلسل الٹیاں آ رہی ہیں، کچھ بھی اندر نہیں ٹکتا",
            "{subj} صبح سے الٹی رک ہی نہیں رہی، پانی بھی باہر آ جاتا ہے",
            "{subj} بار بار الٹی ہو رہی ہے، او آر ایس بھی واپس نکل جاتا ہے",
            "{subj} مسلسل الٹی ہو رہی ہے اور شوگر بہت زیادہ ہے",
            "{subj} پانی کا گھونٹ بھی نہیں رکتا، فوراً الٹی آ جاتی ہے",
            "{subj} لگاتار الٹیاں ہو رہی ہیں کچھ ہضم نہیں ہوتا",
            "{subj} الٹی رکنے کا نام نہیں لے رہی، شدید نڈھال ہیں",
        ],
    }

    ur_subjects = [
        "مجھے", "امی کو", "ابو کو", "دادا کو", "دادی کو", "نانی کو",
        "میرے شوہر کو", "میری بیوی کو", "بچوں کے ابو کو", "ان کو", "اسے", "وہ"
    ]

    all_positives = []
    pid = 1

    # Generate English Positives
    for cat, tmpls in en_pos_templates.items():
        for tmpl in tmpls:
            for subj in en_subjects:
                text = tmpl.format(subj=subj)
                all_positives.append({
                    "id": pid,
                    "text": text,
                    "is_emergency": True,
                    "expected_category": cat,
                    "language": "en",
                    "family": cat,
                })
                pid += 1

    # Generate Roman Urdu Positives (with spelling combinatorics)
    for cat, tmpls in ur_latn_pos_templates.items():
        for tmpl in tmpls:
            for subj in ur_latn_subjects:
                prep = random.choice(ur_latn_preps)
                press = random.choice(ur_latn_press)
                neg_verb = random.choice(ur_latn_neg_verbs)
                v_form = random.choice(ur_latn_v_forms)
                text = tmpl.format(subj=subj, prep=prep, press=press, neg_verb=neg_verb, v_form=v_form)
                all_positives.append({
                    "id": pid,
                    "text": text,
                    "is_emergency": True,
                    "expected_category": cat,
                    "language": "ur-Latn",
                    "family": cat,
                })
                pid += 1

    # Generate Urdu Script Positives
    for cat, tmpls in ur_pos_templates.items():
        for tmpl in tmpls:
            for subj in ur_subjects:
                text = tmpl.format(subj=subj)
                all_positives.append({
                    "id": pid,
                    "text": text,
                    "is_emergency": True,
                    "expected_category": cat,
                    "language": "ur",
                    "family": cat,
                })
                pid += 1

    # Sample num_positives
    sampled_positives = random.sample(all_positives, min(num_positives, len(all_positives)))

    # =========================================================================
    # 2. NEGATIVES GENERATOR
    # =========================================================================
    all_negatives = []
    nid = 1

    # Group A: Preceding Negations
    en_prec_negs = [
        "I have no chest pain and no breathing trouble",
        "Patient denies chest tightness, breathing is fine",
        "Zero shortness of breath, feeling quite comfortable",
        "Without any chest pain or palpitations today",
        "No face droop, no arm weakness, speech is clear",
        "No fainting or loss of consciousness whatsoever",
        "Did not vomit at all, keeping fluids down easily",
        "Never had any difficulty breathing or chest squeeze",
        "No slurred speech, no facial drooping, feeling normal",
        "No vomiting, taking water and food normally",
    ]
    ur_latn_prec_negs = [
        "koi seene me dard ya dabao nahi hai",
        "seene me koi jakran ya bojh nahi mehsoos ho raha",
        "sans ki koi takleef nahi hai, bilkul normal hai",
        "bina kisi sans ki takleef ke theek thaak hoon",
        "chehra bilkul theek hai, koi terha pan nahi",
        "zaban nahi larkharai, bolna bilkul saaf hai",
        "koi behoshi ya ghashi nahi hui",
        "hosh bilkul theek hai, chakkar nahi aye",
        "ulti bilkul nahi hui, khana peena theek hai",
        "koi ulti ya matli nahi hai, paani thehar raha hai",
    ]
    ur_prec_negs = [
        "سینے میں کوئی درد یا دباؤ نہیں ہے",
        "سینے میں کوئی جکڑن یا بوجھ محسوس نہیں ہو رہا",
        "سانس کی کوئی تکلیف نہیں ہے، بالکل نارمل ہے",
        "بغیر کسی سانس کی تکلیف کے ٹھیک ٹھاک ہوں",
        "چہرہ بالکل ٹھیک ہے، کوئی ٹیڑھا پن نہیں",
        "زبان نہیں لڑکھڑائی، بولنا بالکل صاف ہے",
        "کوئی بے ہوشی یا غشی نہیں ہوئی",
        "ہوش بالکل ٹھیک ہے، چکر نہیں آئے",
        "الٹی بالکل نہیں ہوئی، کھانا پینا ٹھیک ہے",
        "کوئی الٹی یا متلی نہیں ہے، پانی ٹھہر رہا ہے",
    ]

    # Group B: Trailing Negation Frames
    en_trail_negs = [
        "Chest pain did not happen at all",
        "Breathing trouble was not an issue today",
        "Fainting or loss of consciousness was absent",
        "Slurred speech was never observed",
        "Arm weakness or paralysis did not occur",
        "Vomiting fluids was completely avoided",
        "Suffocation or choking was not experienced",
        "Facial drooping did not take place",
    ]
    ur_latn_trail_negs = [
        "seene me dard hone wali koi baat nahi hui",
        "sans ukhadne jaisi koi takleef nahi hai",
        "behosh hone wali koi baat nahi thi",
        "ghashi aane jaisa kuch nahi hua",
        "munh terha hone ka koi masla nahi hua",
        "bazu kamzor hone wali baat nahi hai",
        "ulti aane ka koi masla nahi hai ab",
        "dam ghutne jaisi koi baat nahi hui",
    ]
    ur_trail_negs = [
        "سینے میں درد ہونے والی کوئی بات نہیں ہوئی",
        "سانس اکھڑنے جیسی کوئی تکلیف نہیں ہے",
        "بے ہوش ہونے والی کوئی بات نہیں تھی",
        "غشی آنے جیسا کچھ نہیں ہوا",
        "منہ ٹیڑھا ہونے کا کوئی مسئلہ نہیں ہوا",
        "بازو کمزور ہونے والی بات نہیں ہے",
        "الٹی آنے کا کوئی مسئلہ نہیں ہے اب",
        "دم گھٹنے جیسی کوئی بات نہیں ہوئی",
    ]

    # Group C: Echo-Question & Short-Answer Negations (R5.3)
    en_echo_negs = [
        "chest pain? no", "chest tightness? nope", "severe chest pressure: not at all",
        "breathing trouble? no", "shortness of breath - none", "choking? not really",
        "face drooping? no", "slurred speech? nope", "arm weakness? not at all",
        "fainting? no", "loss of consciousness? never", "unresponsive? nope",
        "vomiting fluids? no", "throwing up? not really", "dizzy? no",
    ]
    ur_latn_echo_negs = [
        "seene me dard? nahi", "seene ka dabao: bilkul nahi", "seenay me bojh? nai",
        "sans ki takleef? nahi", "dam ghutna - bilkul nahi", "sans phoolna? nahi",
        "chehra terha? nahi", "bolne me dushwari: nahi hui", "bazu bejaan? bilkul nahi",
        "behosh hue? nahi", "ghashi aayi? nahi", "hosh kho baithe? nahi",
        "ulti ho rahi? nahi", "pani nikal raha? bilkul nahi", "chakkar? nahi",
    ]
    ur_echo_negs = [
        "سینے میں درد؟ نہیں", "سینے کا دباؤ: بالکل نہیں", "سینے میں بوجھ؟ نہیں",
        "سانس کی تکلیف؟ نہیں", "دم گھٹنا - بالکل نہیں", "سانس پھولنا؟ نہیں",
        "چہرہ ٹیڑھا؟ نہیں", "بولنے میں دشواری: نہیں ہوئی", "بازو بے جان؟ بالکل نہیں",
        "بے ہوش ہوئے؟ نہیں", "غشی آئی؟ نہیں", "ہوش کھو بیٹھے؟ نہیں",
        "الٹی ہو رہی؟ نہیں", "پانی نکل رہا؟ بالکل نہیں", "چکر؟ نہیں",
    ]

    # Group D: Remote-Past Resolved History
    en_past_negs = [
        "Had mild chest tightness two years ago, fully resolved now",
        "Had shortness of breath during asthma attack in childhood, fine now",
        "Suffered a fainting spell 10 years back, perfectly healthy today",
        "Had a stroke 5 years ago, recovered completely with normal power",
        "Vomited once last week after bad food, completely stopped now",
        "Passed out once back in 2018, tests were all clear",
    ]
    ur_latn_past_negs = [
        "paanch saal pehle seene me dabao hua tha, ab bilkul theek hoon",
        "bachpan me sans ki takleef hui thi, ab koi masla nahi",
        "das saal pehle behosh hua tha, ab bilkul theek hai",
        "pichle hafte ek bar ulti aayi thi kharab khane se, ab theek hoon",
        "teen saal pehle falij hua tha magar ab poori harkat wapas aa chuki hai",
        "do maheene pehle chakkar aye the doctor ne check kiya sab normal tha",
    ]
    ur_past_negs = [
        "پانچ سال پہلے سینے میں دباؤ ہوا تھا، اب بالکل ٹھیک ہوں",
        "بچپن میں سانس کی تکلیف ہوئی تھی، اب کوئی مسئلہ نہیں",
        "دس سال پہلے بے ہوش ہوا تھا، اب بالکل ٹھیک ہے",
        "پچھلے ہفتے ایک بار الٹی آئی تھی خراب کھانے سے، اب ٹھیک ہوں",
        "تین سال پہلے فالج ہوا تھا مگر اب پوری حرکت واپس آ چکی ہے",
        "دو مہینے پہلے چکر آئے تھے ڈاکٹر نے چیک کیا سب نارمل تھا",
    ]

    # Group E: Benign Activity / Postural Numbness
    en_benign_posture_negs = [
        "My arm went numb when I slept on it, completely fine now",
        "Hand felt tingling after using mobile for long hours, resolved now",
        "Leg was asleep from sitting cross legged on floor, fine in 2 minutes",
        "Left hand had pins and needles from resting on desk, ok now",
        "Fingers were slightly numb from holding cold bottle, back to normal",
    ]
    ur_latn_benign_posture_negs = [
        "haath sunn ho gaya tha jab us par so gaya tha, ab theek hai",
        "der tak mobile chalane se ungliyan sunn ho gayi theen, ab normal hain",
        "chokri maar kar baithne se taang so gayi thi, do minute me theek ho gayi",
        "bazu par sar rakh kar sone se sunn hua tha, ab bilkul theek hai",
        "der tak ek hi position me baithne se pairo me jhanjhanahat thi, theek ho gayi",
    ]
    ur_benign_posture_negs = [
        "ہاتھ سن ہو گیا تھا جب اس پر سو گیا تھا، اب ٹھیک ہے",
        "دیر تک موبائل چلانے سے انگلیاں سن ہو گئی تھیں، اب نارمل ہیں",
        "چوکڑی مار کر بیٹھنے سے ٹانگ سو گئی تھی، دو منٹ میں ٹھیک ہو گئی",
        "بازو پر سر رکھ کر سونے سے سن ہوا تھا، اب بالکل ٹھیک ہے",
        "دیر تک ایک ہی پوزیشن میں بیٹھنے سے پیروں میں جھنجھناہٹ تھی، ٹھیک ہو گئی",
    ]

    # Group F: Benign Spicy Food Heartburn
    en_heartburn_negs = [
        "Mild heartburn after having very spicy biryani, fine after milk",
        "Acid reflux and burning after oily fried dinner, no chest pain",
        "Stomach burning sensation from chili food, settled after antacid",
        "Feeling slight acidity in throat after eating fast food",
    ]
    ur_latn_heartburn_negs = [
        "tez mirch wala khana khane ke baad seene me halki jalan hai",
        "tali hui cheezein khane se acidity ho gayi hai magar koi dard nahi",
        "masalay dar biryani se seene me jalan hui antacid lene se theek ho gayi",
        "khanay ke baad tez jalan thi doodh peene se theek ho gayi",
    ]
    ur_heartburn_negs = [
        "تیز مرچ والا کھانا کھانے کے بعد سینے میں ہلکی جلن ہے",
        "تلی ہوئی چیزیں کھانے سے تیزابیت ہو گئی ہے مگر کوئی درد نہیں",
        "مصالحے دار بریانی سے سینے میں جلن ہوئی اینٹاسڈ لینے سے ٹھیک ہو گئی",
        "کھانے کے بعد تیز جلن تھی دودھ پینے سے ٹھیک ہو گئی",
    ]

    # Group G: Bare Negatives & Routine Statements
    en_routine_negs = [
        "no", "nope", "nah", "none", "not at all", "feeling totally fine today",
        "routine blood pressure check, feeling great", "all good today, no symptoms",
        "fasting sugar is 110, no complaints", "took medicines on time, feeling well",
    ]
    ur_latn_routine_negs = [
        "nahi", "nai", "nahin", "nhi", "bilkul nahi", "na", "aaj tabiyat bilkul theek hai",
        "routine checkup hai koi masla nahi", "sab theek hai alhamdulillah",
        "sugar 120 aayi hai koi takleef nahi", "dawai waqt par li hai bilkul theek hoon",
    ]
    ur_routine_negs = [
        "نہیں", "بالکل نہیں", "کوئی نہیں", "نہ", "آج طبیعت بالکل ٹھیک ہے",
        "روٹین چیک اپ ہے کوئی مسئلہ نہیں", "سب ٹھیک ہے الحمدللہ",
        "شوگر ۱۲۰ آئی ہے کوئی تکلیف نہیں", "دوائی وقت پر لی ہے بالکل ٹھیک ہوں",
    ]

    all_neg_sources = [
        (en_prec_negs, "en", "preceding_negation"),
        (ur_latn_prec_negs, "ur-Latn", "preceding_negation"),
        (ur_prec_negs, "ur", "preceding_negation"),
        (en_trail_negs, "en", "trailing_negation"),
        (ur_latn_trail_negs, "ur-Latn", "trailing_negation"),
        (ur_trail_negs, "ur", "trailing_negation"),
        (en_echo_negs, "en", "echo_negation"),
        (ur_latn_echo_negs, "ur-Latn", "echo_negation"),
        (ur_echo_negs, "ur", "echo_negation"),
        (en_past_negs, "en", "remote_past"),
        (ur_latn_past_negs, "ur-Latn", "remote_past"),
        (ur_past_negs, "ur", "remote_past"),
        (en_benign_posture_negs, "en", "benign_posture"),
        (ur_latn_benign_posture_negs, "ur-Latn", "benign_posture"),
        (ur_benign_posture_negs, "ur", "benign_posture"),
        (en_heartburn_negs, "en", "benign_heartburn"),
        (ur_latn_heartburn_negs, "ur-Latn", "benign_heartburn"),
        (ur_heartburn_negs, "ur", "benign_heartburn"),
        (en_routine_negs, "en", "routine_normal"),
        (ur_latn_routine_negs, "ur-Latn", "routine_normal"),
        (ur_routine_negs, "ur", "routine_normal"),
    ]

    # Generate Negatives by applying slight variations and combinatorics
    subject_prefixes_en = ["", "Today, ", "In check-in: ", "I report ", "Patient says: "]
    subject_prefixes_ur_latn = ["", "aaj ", "check-in mein: ", "mareez kehta hai: ", "bhai "]
    subject_prefixes_ur = ["", "آج ", "چیک ان میں: ", "مریض نے کہا: "]

    for source_list, lang, family in all_neg_sources:
        prefixes = subject_prefixes_en if lang == "en" else (subject_prefixes_ur_latn if lang == "ur-Latn" else subject_prefixes_ur)
        for text in source_list:
            for pfx in prefixes:
                var_text = pfx + text
                all_negatives.append({
                    "id": nid,
                    "text": var_text.strip(),
                    "is_emergency": False,
                    "expected_category": None,
                    "language": lang,
                    "family": family,
                })
                nid += 1

    sampled_negatives = random.sample(all_negatives, min(num_negatives, len(all_negatives)))

    # Re-index
    combined = []
    idx = 1
    for p in sampled_positives:
        p["id"] = idx
        combined.append(p)
        idx += 1
    for n in sampled_negatives:
        n["id"] = idx
        combined.append(n)
        idx += 1

    output_path = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "red_flag_heldout_r5.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)

    print(f"Generated {len(combined)} held-out examples:")
    print(f"  Positives: {len(sampled_positives)}")
    print(f"  Negatives: {len(sampled_negatives)}")
    print(f"Saved to: {output_path}")
    return combined


if __name__ == "__main__":
    generate_corpus(seed=42, num_positives=700, num_negatives=700)
