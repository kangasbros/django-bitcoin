# Create your views here.
from django_bitcoin.forms import BitcoinEscrowBuyForm

def buy_escrow(request):
    """docstring for buy_escrow"""
    if request.method == "POST":
        escrow_form=BitcoinEscrowBuyForm(request.POST)
        if escrow_form.is_valid():
            coi=composeCheckoutFiInfoForWallet(request.user, 
                addpayment_form.cleaned_data["amount"], 
                u"Vannehaku.fi kukkaro "+str(addpayment_form.cleaned_data["amount"])+" eur")
            if "success_redirect_url" in request.POST and request.POST["success_redirect_url"]:
                coi.success_redirect_url=request.POST["success_redirect_url"].strip()
                coi.save()
            return render_to_response("payments/addpayment.html", {
                "coi": coi,
                "addpayment_form": addpayment_form,
            }, context_instance=RequestContext(request))
    else:
        addpayment_form=AddPaymentForm()
    return render_to_response("payments/addpayment.html", {
        "coi": None,
        "addpayment_form": addpayment_form,
    }, context_instance=RequestContext(request))
