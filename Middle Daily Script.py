import pyodbc
import pandas as pd
import os 
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime, timedelta

import time

def open_browser_and_go_to_url(url):
    options = Options()
    # options.add_argument("--headless")

    # Selenium Manager auto-installs correct driver
    driver = webdriver.Edge(options=options)
    driver.get(url)
    return driver

def enter_credential(driver):
    time.sleep(2)  # Wait for the page to load
    try:
        # Wait until the input with placeholder='username' is present
        username_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='username']"))
        )
        username_input.send_keys("rle")
        username_input.send_keys(Keys.ENTER)
    except Exception as e:
        print("Failed to find the username input field.")
        print(e)


def clickIssue(driver):
    time.sleep(2)  # Wait for the page to load
    try:
        issue_element = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//p[text()='ISSUE']"))
        )
        issue_element.click()
        print("Successfully clicked using text content")
    except Exception as e:
        print(f"Failed to click using text content: {e}")


def enterTrashPR(driver):
    time.sleep(2)  # Wait for the page to load
    try:
        targetPR = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text']"))
        )
        targetPR.send_keys("58686")
        targetPR.send_keys(Keys.ENTER)
        print("Successfully clicked Entered issued trash PR")
    except Exception as e:
        print(f"Failed to click using text content: {e}")

def issueFunction(driver):
    time.sleep(2)  # Wait for the page to load
    try:
        first_li = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//ul[@class=' nav nav-stacked']/li[1]/a"))
        )
        first_li.click()
        print("Successfully clicked first li element")
    except Exception as e:
        print(f"Failed to click first li: {e}")
    time.sleep(2) 

def pullAndIssue(driver):
    time.sleep(2)  # Wait for the page to load
    try:
        inputField = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text']"))
        )
        conn = pyodbc.connect(
            'DRIVER={SQL Server};'
            'SERVER=192.168.0.10;'
            'DATABASE=PDB_Parity4_SGP;'
            'Trusted_Connection=yes;'
        )

        # Example SQL query
        query = "SELECT ItemID,CreatedDateTime, ProductionLineID, Fill " \
                "FROM dbo.BVW_BTItemLot " \
                "WHERE (ProductID='WIP0900') AND " \
                      "ItemStatus='Available' AND " \
                      "FacilityID='SGP-LEVI' AND " \
                      "LocationID IN ('2ZWP', '2ZESM1', '2ZESM2', '2PICK', '2BLOW', '2ZLMC', '2LMC', '2ESM1', '2ESM2', '2ZMEAL', '2WP')"
        # WIP0900 = FS
        # WIP0146 = WIP TRASH - Blower
        df = pd.read_sql(query, conn)

        with pd.option_context(
                                'display.max_rows', None, 
                                'display.max_columns', None, 
                                'display.width', None
                            ):
            print(df)
        total = 0
        for index, row in df.iterrows():
            item_id = row['ItemID']
            inputField.send_keys(item_id)
            inputField.send_keys(Keys.ENTER)
            total += row['Fill']
            time.sleep(2) 
        conn.close()
        print("Successfully clicked Entered issued trash PR")
        print("Total issued floor sweep: ", total)
    except Exception as e:
        print(f"Failed to click using text content: {e}")


def get_yesterday_string():
    yesterday = datetime.now() - timedelta(days=1)
    return yesterday.strftime('%#m/%#d/%Y 12:00:00 AM')

def trimmingWIP():
    query = f""" 
        SELECT ProductionID 
        FROM dbo.BTProduction_T 
        WHERE PXWorkflowSK = 'A354AB9D-9A6D-E811-80B9-00155D657602' 
        AND ScheduledStartDateTime = '{get_yesterday_string()}'
    """

    conn = pyodbc.connect(
        'DRIVER={SQL Server};'
        'SERVER=192.168.0.10;'
        'DATABASE=PDB_Parity4_SGP;'
        'Trusted_Connection=yes;'
    )
    print('List of WIP PR to Trim')
    df = pd.read_sql(query, conn)
    with pd.option_context('display.max_rows', None, 'display.max_columns', None, 'display.width', None):
        print(df)

    cursor = conn.cursor()
    
    for index, row in df.iterrows():
        PR = row['ProductionID']
        print(f"Trimming PR: {PR}")

        trimmingQueryProduce = f"""
            DELETE a
            FROM dbo.BTProductionProduct_T AS a
            LEFT JOIN dbo.BTProductionProductItem_T AS b
                ON a.BTProductionProduct_TSK = b.BTProductionProduct_TSK
            WHERE a.BTProduction_TSK = (
                SELECT BTProduction_TSK
                FROM dbo.BTProduction_T
                WHERE ProductionID = '{PR}'
            )
            AND b.BTProductionProduct_TSK IS NULL;
        """

        trimmingQueryIssue = f"""
            DELETE a
            FROM dbo.BTProductionIssue_T AS a
            LEFT JOIN dbo.BTProductionIssueItemLot_T AS b
                ON a.BTProductionIssue_TSK = b.BTProductionIssue_TSK
            WHERE a.BTProduction_TSK = (
                SELECT BTProduction_TSK
                FROM dbo.BTProduction_T
                WHERE ProductionID = '{PR}'
            )
            AND b.BTProductionIssue_TSK IS NULL;
        """

        # Execute and capture row count for each
        cursor.execute(trimmingQueryProduce)
        affected_produce = cursor.rowcount
        print(f"Deleted from BTProductionProduct_T: {affected_produce} rows")

        cursor.execute(trimmingQueryIssue)
        affected_issue = cursor.rowcount
        print(f"Deleted from BTProductionIssue_T: {affected_issue} rows")

        conn.commit()  # Commit after both deletes
        time.sleep(2)

    cursor.close()
    conn.close()

def trimmingFinishedGoods():
    query = f""" 
        SELECT ProductionID 
        FROM dbo.BTProduction_T 
        WHERE PXWorkflowSK = 'A754AB9D-9A6D-E811-80B9-00155D657602' 
        AND NOTE LIKE '%WEIGH PACK%'
        AND ScheduledStartDateTime = '{get_yesterday_string()}'
    """

    conn = pyodbc.connect(
        'DRIVER={SQL Server};'
        'SERVER=192.168.0.10;'
        'DATABASE=PDB_Parity4_SGP;'
        'Trusted_Connection=yes;'
    )

    print('Trimming WP PR:')
    df = pd.read_sql(query, conn)
    with pd.option_context('display.max_rows', None, 'display.max_columns', None, 'display.width', None):
        print(df)

    cursor = conn.cursor()
    for index, row in df.iterrows():
        PR = row['ProductionID']
        print(f"Trimming PR: {PR}")

        trimmingQueryProduce = f"""
            DELETE a
            FROM dbo.BTProductionProduct_T AS a
            LEFT JOIN dbo.BTProductionProductItem_T AS b
                ON a.BTProductionProduct_TSK = b.BTProductionProduct_TSK
            WHERE a.BTProduction_TSK = (
                SELECT BTProduction_TSK
                FROM dbo.BTProduction_T
                WHERE ProductionID = '{PR}'
            )
            AND b.BTProductionProduct_TSK IS NULL;
        """

        trimmingQueryIssue = f"""
            DELETE a
            FROM dbo.BTProductionIssue_T AS a
            LEFT JOIN dbo.BTProductionIssueItemLot_T AS b
                ON a.BTProductionIssue_TSK = b.BTProductionIssue_TSK
            WHERE a.BTProduction_TSK = (
                SELECT BTProduction_TSK
                FROM dbo.BTProduction_T
                WHERE ProductionID = '{PR}'
            )
            AND b.BTProductionIssue_TSK IS NULL;
        """

        # Execute and capture row count for each
        cursor.execute(trimmingQueryProduce)
        affected_produce = cursor.rowcount
        print(f"Deleted from BTProductionProduct_T: {affected_produce} rows")

        cursor.execute(trimmingQueryIssue)
        affected_issue = cursor.rowcount
        print(f"Deleted from BTProductionIssue_T: {affected_issue} rows")

        conn.commit()  # Commit after both deletes
        time.sleep(2)

    cursor.close()
    conn.close()


# Run everything
print(' ------------------------------ ISSUING TRASH -----------------------------')
time.sleep(2) 
driver = open_browser_and_go_to_url("http://192.168.0.10/SGP_Mobile")
enter_credential(driver)
clickIssue(driver)
enterTrashPR(driver)
issueFunction(driver)
pullAndIssue(driver)
driver.quit()

print(' ------------------------------ TRIMMING PR-----------------------------')
time.sleep(2) 
trimmingWIP()
trimmingFinishedGoods()