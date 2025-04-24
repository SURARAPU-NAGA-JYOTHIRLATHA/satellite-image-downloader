import streamlit as st
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import urllib.parse

SAVE_FOLDER = "satellite_images"
os.makedirs(SAVE_FOLDER, exist_ok=True)

def capture_satellite_image(lat, lon, zoom=17): # Added zoom parameter
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--window-size=1920x1080") # Ensure large enough window
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--lang=en-US") # Set language to potentially stabilize selectors/UI
    options.add_experimental_option('excludeSwitches', ['enable-logging']) # Suppress console logs

    driver = None # Initialize driver to None for finally block
    try:
        print("Initializing WebDriver...")
        driver = webdriver.Chrome(
            service=webdriver.chrome.service.Service(ChromeDriverManager().install()),
            options=options
        )
        wait = WebDriverWait(driver, 25) # Increase wait time slightly

        # --- Construct URL for direct satellite view ---
        # Option 1: Using @ coordinates and /data parameter (often works well)
        # Example: https://www.google.com/maps/@16.242488,81.229445,17z/data=!3m1!1e3?entry=ttu
        # The /data parameter part can be complex. Let's try a simpler q=lat,lon&t=k first.

        # Option 2: Using q=lat,lon and t=k parameter (classic satellite view)
        # Example: https://www.google.com/maps?q=16.242488,81.229445&hl=en&t=k&z=17
        map_url = f"https://www.google.com/maps?q={lat},{lon}&hl=en&t=k&z={zoom}"

        # Option 3: Let's try the @ coordinates format which might be more stable
        # map_url = f"https://www.google.com/maps/@{lat},{lon},{zoom}z?hl=en&entry=ttu"
        # This one might require clicking satellite manually still. Stick with Option 2 for now.

        print(f"Navigating directly to satellite view URL: {map_url}")
        driver.get(map_url)

        # --- Consent Screen Handling (Still potentially needed) ---
        try:
            print("Checking for consent screen...")
            # More general XPath for buttons within the consent dialog
            consent_button_xpath = "//div[contains(@class, 'consent')]//button[.//span[contains(text(), 'Accept all') or contains(text(), 'Reject all') or contains(text(), 'Agree')]]"
            consent_button = WebDriverWait(driver, 7).until(
                EC.element_to_be_clickable((By.XPATH, consent_button_xpath))
            )
            # Use JS click for potential overlay issues
            driver.execute_script("arguments[0].click();", consent_button)
            print("Clicked consent button.")
            time.sleep(2) # Pause after consent click
        except TimeoutException:
            print("No consent screen found or timed out.")
        except Exception as e:
            print(f"Error handling consent screen: {e}")

        # --- Wait for Satellite Tiles to Load ---
        # Since we loaded directly into satellite mode, we primarily need to wait for rendering.
        # Waiting for a specific element is hard, so a longer sleep is pragmatic.
        print(f"Waiting for satellite map tiles to load at zoom {zoom}...")
        time.sleep(10) # Increased wait time - crucial for satellite tiles in headless mode!

        # --- Optional: Check if search box overlay is present and close it ---
        try:
             # This small 'x' button often appears over the map after a direct URL load
             close_button_selector = "button[aria-label='Close']" # General close button
             close_button = WebDriverWait(driver, 3).until(
                 EC.element_to_be_clickable((By.CSS_SELECTOR, close_button_selector))
             )
             # Check if it's likely the search result close button (often associated with specific parent classes)
             # This check is fragile, but tries to avoid closing unrelated things
             parent_div = close_button.find_element(By.XPATH, "./../..") # Go up two levels
             if 'xoLG9e' in parent_div.get_attribute('class'): # Example class, INSPECT BROWSER TO CONFIRM
                 print("Found and closing search result overlay...")
                 close_button.click()
                 time.sleep(1)
        except TimeoutException:
             print("No obvious search overlay close button found.")
        except Exception as e:
             print(f"Minor error trying to close search overlay: {e}")


        # --- Take Screenshot ---
        filename = f"satellite_{lat}_{lon}_z{zoom}.png"
        filepath = os.path.join(SAVE_FOLDER, filename)
        print(f"Saving screenshot to {filepath}...")

        # Try capturing just the map canvas for a cleaner image (more complex)
        # try:
        #    map_canvas = driver.find_element(By.CSS_SELECTOR, ".mapsConsumerUiSceneInternalCoreScene__widget-scene-canvas") # Selector might change
        #    map_canvas.screenshot(filepath)
        # except Exception as e:
        #    print(f"Could not screenshot map canvas only ({e}), taking full page screenshot.")
        #    driver.save_screenshot(filepath) # Fallback

        # Simple full page screenshot
        if not driver.save_screenshot(filepath):
             print("Error: driver.save_screenshot returned False.")
             raise IOError(f"Failed to save screenshot to {filepath}")

        print("Screenshot saved.")
        return filepath

    except Exception as e:
        print(f"An error occurred in capture_satellite_image: {e}")
        # Try to capture a debug screenshot if something went wrong
        if driver:
            try:
                # Ensure filename uniqueness for debug screenshot
                timestamp = time.strftime("%Y%m%d-%H%M%S")
                debug_path = os.path.join(SAVE_FOLDER, f"debug_{lat}_{lon}_{timestamp}.png")
                driver.save_screenshot(debug_path)
                print(f"Saved debug screenshot to {debug_path}")
            except Exception as E:
                 print(f"Failed to save debug screenshot: {E}")
        return None # Indicate failure
    finally:
        if driver:
            print("Closing WebDriver.")
            driver.quit()

# Streamlit UI (Added zoom slider)
st.title("🌍 Satellite Image Downloader")
st.markdown("""
Enter latitude and longitude to download a satellite image from Google Maps.""")

# Use coordinates from your target image
lat_default = "16.242488"
lon_default = "81.229445"

# Removed default coordinates
lat = st.text_input("Latitude", "")
lon = st.text_input("Longitude", "")
zoom_level = st.slider("Zoom Level (Higher = More Zoomed In)", min_value=10, max_value=21, value=17, step=1)

if st.button("📸 Download Satellite Image"):
    with st.spinner(f"Loading map and capturing satellite view at zoom {zoom_level}... Please wait (this can take 20-40 seconds)..."):
        image_path = capture_satellite_image(lat, lon, zoom=zoom_level) # Pass zoom level

        if image_path and os.path.exists(image_path):
            st.success("✅ Image captured successfully!")
            st.image(image_path, caption=f"Satellite Image (Zoom: {zoom_level})", use_column_width=True)

            with open(image_path, "rb") as file:
                st.download_button(
                    label="📥 Download Image",
                    data=file,
                    file_name=os.path.basename(image_path),
                    mime="image/png"
                )
        elif image_path is None:
             st.error("❌ Image capture failed. Check console/terminal logs for details.")
        else:
            st.error("❌ Image capture failed and no file was created (unknown error).")