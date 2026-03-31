"""Gardiner Sign List — complete reference data.

Aggregates all per-category sign data into a single flat list.
Each sign is a tuple:
    (code, hex, description, phonetic, type, logographic, det_class)
"""

from __future__ import annotations

from app.core.gardiner_data.a_man import SIGNS as _A_SIGNS
from app.core.gardiner_data.aa_unclassified import SIGNS as _AA_SIGNS
from app.core.gardiner_data.b_woman import SIGNS as _B_SIGNS
from app.core.gardiner_data.c_deities import SIGNS as _C_SIGNS
from app.core.gardiner_data.d_body import SIGNS as _D_SIGNS
from app.core.gardiner_data.e_mammals import SIGNS as _E_SIGNS
from app.core.gardiner_data.f_parts_mammals import SIGNS as _F_SIGNS
from app.core.gardiner_data.g_birds import SIGNS as _G_SIGNS
from app.core.gardiner_data.h_parts_birds import SIGNS as _H_SIGNS
from app.core.gardiner_data.i_reptiles import SIGNS as _I_SIGNS
from app.core.gardiner_data.k_fish import SIGNS as _K_SIGNS
from app.core.gardiner_data.l_invertebrates import SIGNS as _L_SIGNS
from app.core.gardiner_data.m_plants import SIGNS as _M_SIGNS
from app.core.gardiner_data.n_sky_earth import SIGNS as _N_SIGNS
from app.core.gardiner_data.o_buildings import SIGNS as _O_SIGNS
from app.core.gardiner_data.p_ships import SIGNS as _P_SIGNS
from app.core.gardiner_data.q_furniture import SIGNS as _Q_SIGNS
from app.core.gardiner_data.r_temple import SIGNS as _R_SIGNS
from app.core.gardiner_data.s_crowns import SIGNS as _S_SIGNS
from app.core.gardiner_data.t_warfare import SIGNS as _T_SIGNS
from app.core.gardiner_data.u_agriculture import SIGNS as _U_SIGNS
from app.core.gardiner_data.v_rope import SIGNS as _V_SIGNS
from app.core.gardiner_data.w_vessels import SIGNS as _W_SIGNS
from app.core.gardiner_data.x_loaves import SIGNS as _X_SIGNS
from app.core.gardiner_data.y_writings import SIGNS as _Y_SIGNS
from app.core.gardiner_data.z_strokes import SIGNS as _Z_SIGNS

ALL_SIGNS: list[tuple[str, int, str, str, str, str, str]] = []
ALL_SIGNS.extend(_A_SIGNS)
ALL_SIGNS.extend(_B_SIGNS)
ALL_SIGNS.extend(_C_SIGNS)
ALL_SIGNS.extend(_D_SIGNS)
ALL_SIGNS.extend(_E_SIGNS)
ALL_SIGNS.extend(_F_SIGNS)
ALL_SIGNS.extend(_G_SIGNS)
ALL_SIGNS.extend(_H_SIGNS)
ALL_SIGNS.extend(_I_SIGNS)
ALL_SIGNS.extend(_K_SIGNS)
ALL_SIGNS.extend(_L_SIGNS)
ALL_SIGNS.extend(_M_SIGNS)
ALL_SIGNS.extend(_N_SIGNS)
ALL_SIGNS.extend(_O_SIGNS)
ALL_SIGNS.extend(_P_SIGNS)
ALL_SIGNS.extend(_Q_SIGNS)
ALL_SIGNS.extend(_R_SIGNS)
ALL_SIGNS.extend(_S_SIGNS)
ALL_SIGNS.extend(_T_SIGNS)
ALL_SIGNS.extend(_U_SIGNS)
ALL_SIGNS.extend(_V_SIGNS)
ALL_SIGNS.extend(_W_SIGNS)
ALL_SIGNS.extend(_X_SIGNS)
ALL_SIGNS.extend(_Y_SIGNS)
ALL_SIGNS.extend(_Z_SIGNS)
ALL_SIGNS.extend(_AA_SIGNS)

SIGN_INDEX: dict[str, tuple[str, int, str, str, str, str, str]] = {
    s[0]: s for s in ALL_SIGNS
}
