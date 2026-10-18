TRANSITIONS = {
    ("draft", "buyer_agrees"): "agreed",
    ("draft", "seller_agrees"): "agreed",
    ("agreed", "buyer_agrees"): "agreed",
    ("agreed", "seller_agrees"): "agreed",
    ("agreed", "deposit_confirmed"): "funded",
    ("funded", "conditions_checked"): "conditions_met",
    ("funded", "refund_confirmed"): "refunded",
    ("conditions_met", "registration_recorded"): "registered",
    ("conditions_met", "refund_confirmed"): "refunded",
    ("registered", "release_confirmed"): "released",
    ("funded", "deadline_passed"): "refunded",
    ("conditions_met", "deadline_passed"): "refunded",
    ("draft", "cancel"): "cancelled",
    ("agreed", "cancel"): "cancelled",
}


def transition(state: str, event: str) -> str:
    try:
        return TRANSITIONS[(state, event)]
    except KeyError:
        raise ValueError("এই অবস্থায় এই কাজটি করা যাবে না।") from None
