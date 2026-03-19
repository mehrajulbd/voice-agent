import sys
import os

# Add parent directory to path to enable imports from services/, call/, etc.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from services.product_service import ProductService
from call_runner import place_call_sync

# Page configuration
st.set_page_config(
    page_title="Order System - চালডাল ডট কম",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better UI
st.markdown("""
<style>
    .product-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #ddd;
        margin-bottom: 1rem;
    }
    .product-card:hover {
        border-color: #ff4b4b;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .price-tag {
        font-size: 1.2rem;
        font-weight: bold;
        color: #2e7d32;
    }
    .call-status {
        padding: 1.5rem;
        border-radius: 0.5rem;
        background-color: #e3f2fd;
        margin: 1rem 0;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #e8f5e9;
        border-left: 4px solid #4caf50;
        color: #1b5e20;  /* Dark green text for better readability */
        margin: 1rem 0;
    }
    .error-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #ffebee;
        border-left: 4px solid #f44336;
        color: #b71c1c;  /* Dark red text for better readability */
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'selected_product' not in st.session_state:
    st.session_state.selected_product = None
if 'quantity' not in st.session_state:
    st.session_state.quantity = 1
if 'phone_number' not in st.session_state:
    st.session_state.phone_number = ""
if 'language' not in st.session_state:
    st.session_state.language = "bn-BD"
if 'call_state' not in st.session_state:
    st.session_state.call_state = 'product_selection'  # product_selection, checkout, calling, results
if 'call_result' not in st.session_state:
    st.session_state.call_result = None


def reset_to_catalog():
    """Reset to product selection."""
    st.session_state.selected_product = None
    st.session_state.quantity = 1
    st.session_state.phone_number = ""
    st.session_state.call_state = 'product_selection'
    st.session_state.call_result = None


def go_to_checkout(product_id):
    """Navigate to checkout with selected product."""
    st.session_state.selected_product = product_id
    st.session_state.call_state = 'checkout'


def place_order():
    """Place the call order."""
    st.session_state.call_state = 'calling'


def display_header():
    """Display the app header."""
    product_service = ProductService()
    company = product_service.get_company_name()

    col1, col2 = st.columns([1, 4])
    with col1:
        st.markdown("## 🛒")
    with col2:
        st.markdown(f"## {company}")
    st.markdown("---")


def product_selection_page():
    """Display product catalog page."""
    st.markdown("### 📦 Select a Product")

    product_service = ProductService()
    products = product_service.get_all_products()

    # Display products as grid
    cols = st.columns(3)
    for idx, product in enumerate(products):
        with cols[idx % 3]:
            with st.container():
                st.markdown(f"#### {product.name}")
                if product.name_en != product.name:
                    st.markdown(f"*{product.name_en}*")
                st.markdown(f"**Price:** ৳{product.price_per_unit:.2f} / {product.unit}")
                st.markdown(f"**Default Qty:** {product.default_quantity} {product.unit}")

                if st.button(f"Select →", key=f"select_{product.id}", use_container_width=True):
                    st.session_state.selected_product = product
                    st.session_state.call_state = 'checkout'
                    st.rerun()

                st.markdown("<br>", unsafe_allow_html=True)


def checkout_page():
    """Display checkout form."""
    product_service = ProductService()
    product = product_service.get_product(st.session_state.selected_product.id)

    st.markdown("### 🛍️ Checkout")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown(f"#### {product.name}")
        if product.name_en != product.name:
            st.markdown(f"*{product.name_en}*")

        # Quantity input
        quantity = st.number_input(
            "Quantity",
            min_value=1,
            max_value=1000,
            value=st.session_state.get('quantity', product.default_quantity),
            step=1,
            help=f"Enter quantity in {product.unit}"
        )
        st.session_state.quantity = quantity

        # Phone number input
        phone = st.text_input(
            "Phone Number (E.164 format)",
            value=st.session_state.get('phone_number', ''),
            placeholder="+8801327403936",
            help="Include country code, e.g., +880 for Bangladesh"
        )
        st.session_state.phone_number = phone

        # Language selection (optional)
        language = st.selectbox(
            "Language (Optional)",
            options=["bn-BD", "bn-IN"],
            index=0,
            help="Select language for automated call (bn-IN = Bengali, India"
        )
        st.session_state.language = language

        # Total price display
        total = product.price_per_unit * quantity
        st.markdown(f"**Total Price:** ৳{total:.2f} {product.currency}")

        st.markdown("---")

        col_place, col_back = st.columns(2)
        with col_back:
            if st.button("← Back to Catalog", use_container_width=True):
                reset_to_catalog()
                st.rerun()
        with col_place:
            if st.button("✅ Place Call Order", type="primary", use_container_width=True):
                # Validate
                if not phone.startswith("+"):
                    st.error("❌ Phone number must be in E.164 format (e.g., +8801327403936)")
                elif quantity <= 0:
                    st.error("❌ Quantity must be at least 1")
                else:
                    place_order()
                    st.rerun()

    with col2:
        st.markdown("#### Order Summary")
        st.markdown(f"**Product:** {product.name}")
        st.markdown(f"**Quantity:** {quantity} {product.unit}")
        st.markdown(f"**Phone:** {phone if phone else 'Not set'}")


def calling_page():
    """Display calling progress."""
    st.markdown("### 📞 Calling...")

    product_service = ProductService()
    product = product_service.get_product(st.session_state.selected_product.id)

    # Show summary
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**To:** {st.session_state.phone_number}")
        st.markdown(f"**Product:** {product.name}")
        st.markdown(f"**Quantity:** {st.session_state.quantity} {product.unit}")
    with col2:
        st.markdown(f"**Language:** {st.session_state.language}")
        st.markdown(f"**Company:** {product_service.get_company_name()}")

    st.markdown("---")

    # Progress display with a spinner
    with st.spinner("Call in progress... This may take up to 2 minutes."):
        try:
            # Call the runner
            result = place_call_sync(
                phone_number=st.session_state.phone_number,
                product_id=st.session_state.selected_product.id,
                quantity=st.session_state.quantity,
                language_code=st.session_state.language
            )

            st.session_state.call_result = result
            st.session_state.call_state = 'results'
            st.rerun()

        except Exception as e:
            st.error(f"❌ Call failed: {str(e)}")
            st.session_state.call_state = 'results'
            st.rerun()


def results_page():
    """Display call results."""
    result = st.session_state.call_result

    st.markdown("### 📋 Call Results")

    if result.get('success'):
        st.success("✅ Call Completed Successfully")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Phone:** {result['phone_number']}")
            st.markdown(f"**Product:** {result['product_name']}")
            st.markdown(f"**Quantity:** {result['quantity']}")
        with col2:
            st.markdown(f"**Confirmation:** {'✅ Yes' if result['confirmation_detected'] else '❌ No'}")
            st.markdown(f"**Language:** {st.session_state.language}")

        st.markdown("---")
        st.markdown("#### 🎤 Customer Response")
        st.markdown(f'<div style="background-color: #f5f5f520; padding: 1rem; border-radius: 0.5rem; margin: 1rem 0;">{result["transcription"]}</div>', unsafe_allow_html=True)

        if result.get('gemini_analysis'):
            st.markdown("#### 🤖 Analysis")
            st.markdown(f'<div style="background-color: #e8eaf620; padding: 1rem; border-radius: 0.5rem; margin: 1rem 0;">{result["gemini_analysis"]}</div>', unsafe_allow_html=True)

        st.markdown("---")
        st.info(f"📁 Results saved to: `{result.get('result_file', 'N/A')}")

    else:
        st.markdown('<div class="error-box">', unsafe_allow_html=True)
        st.markdown("## ❌ Call Failed")
        st.markdown('</div>', unsafe_allow_html=True)
        st.error(f"Error: {result.get('error', 'Unknown error')}")

    st.markdown("---")

    # Action buttons
    col_new, col_home = st.columns(2)
    with col_new:
        if st.button("🔄 Start New Order", use_container_width=True, type="primary"):
            reset_to_catalog()
            st.rerun()
    with col_home:
        if st.button("🏠 Back to Catalog", use_container_width=True):
            reset_to_catalog()
            st.rerun()


def main():
    """Main app flow."""
    display_header()

    # Check environment variables
    missing_vars = []
    for var in ["LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "SIP_TRUNK_ID", "GOOGLE_API_KEY", "FROM_PHONE_NUMBER"]:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        st.error("⚠️ Missing environment variables!")
        st.markdown("The following environment variables are required:")
        for var in missing_vars:
            st.markdown(f"- `{var}`")
        st.markdown("Please configure your `.env` file and restart the app.")
        st.stop()

    # Route to appropriate page based on state
    if st.session_state.call_state == 'product_selection':
        product_selection_page()
    elif st.session_state.call_state == 'checkout':
        checkout_page()
    elif st.session_state.call_state == 'calling':
        calling_page()
    elif st.session_state.call_state == 'results':
        results_page()


if __name__ == "__main__":
    main()
