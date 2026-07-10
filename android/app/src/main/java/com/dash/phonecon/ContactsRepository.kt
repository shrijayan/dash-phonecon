package com.dash.phonecon

import android.content.ContentProviderOperation
import android.content.ContentValues
import android.content.Context
import android.net.Uri
import android.provider.ContactsContract
import org.json.JSONArray
import org.json.JSONObject

/** One contact as exposed over the wire - id is a RawContacts._ID string. */
data class ContactRecord(val id: String, val name: String, val number: String)

/**
 * Full CRUD against the device's real Contacts provider (ContactsContract),
 * reusing the READ_CONTACTS/WRITE_CONTACTS permissions this app already
 * requests. Deliberately narrow: one name + one number per contact, matching
 * what DashPhoneCon actually needs (dial-by-contact) rather than modeling
 * the full multi-email/multi-address contact schema.
 */
object ContactsRepository {

    /** Returns one row per (name, number) pair - the Phone.CONTENT_URI query
     * can return duplicate rows for the same contact when synced across
     * multiple accounts (e.g. Google + SIM) and can also emit a masked
     * variant of the same number (e.g. "+91 98765 43210" alongside
     * "+919****3210") depending on permission/visibility state, so the
     * dedupe key uses the number's last 4 digits rather than the exact
     * string - masking always preserves the trailing digits. */
    fun listAll(context: Context): List<ContactRecord> {
        val results = mutableListOf<ContactRecord>()
        val seen = HashSet<Pair<String, String>>()
        val projection = arrayOf(
            ContactsContract.CommonDataKinds.Phone.CONTACT_ID,
            ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME,
            ContactsContract.CommonDataKinds.Phone.NUMBER
        )
        context.contentResolver.query(
            ContactsContract.CommonDataKinds.Phone.CONTENT_URI,
            projection,
            null,
            null,
            "${ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME} ASC"
        )?.use { cursor ->
            val idIdx = cursor.getColumnIndexOrThrow(ContactsContract.CommonDataKinds.Phone.CONTACT_ID)
            val nameIdx = cursor.getColumnIndexOrThrow(ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME)
            val numberIdx = cursor.getColumnIndexOrThrow(ContactsContract.CommonDataKinds.Phone.NUMBER)
            while (cursor.moveToNext()) {
                val name = cursor.getString(nameIdx) ?: ""
                val number = cursor.getString(numberIdx) ?: ""
                val digits = number.filter { it.isDigit() }
                val dedupeKey = name to digits.takeLast(4)
                if (!seen.add(dedupeKey)) continue
                results.add(
                    ContactRecord(
                        id = cursor.getLong(idIdx).toString(),
                        name = name,
                        number = number
                    )
                )
            }
        }
        return results
    }

    fun toJsonArray(contacts: List<ContactRecord>): JSONArray {
        val array = JSONArray()
        for (contact in contacts) {
            array.put(
                JSONObject()
                    .put(MessageType.FIELD_CONTACT_ID, contact.id)
                    .put(MessageType.FIELD_NAME, contact.name)
                    .put(MessageType.FIELD_NUMBER, contact.number)
            )
        }
        return array
    }

    /** Creates a new raw contact with one name + one phone number. Returns the new raw contact id. */
    fun add(context: Context, name: String, number: String): String {
        val ops = ArrayList<ContentProviderOperation>()
        ops.add(
            ContentProviderOperation.newInsert(ContactsContract.RawContacts.CONTENT_URI)
                .withValue(ContactsContract.RawContacts.ACCOUNT_TYPE, null)
                .withValue(ContactsContract.RawContacts.ACCOUNT_NAME, null)
                .build()
        )
        ops.add(
            ContentProviderOperation.newInsert(ContactsContract.Data.CONTENT_URI)
                .withValueBackReference(ContactsContract.Data.RAW_CONTACT_ID, 0)
                .withValue(ContactsContract.Data.MIMETYPE, ContactsContract.CommonDataKinds.StructuredName.CONTENT_ITEM_TYPE)
                .withValue(ContactsContract.CommonDataKinds.StructuredName.DISPLAY_NAME, name)
                .build()
        )
        ops.add(
            ContentProviderOperation.newInsert(ContactsContract.Data.CONTENT_URI)
                .withValueBackReference(ContactsContract.Data.RAW_CONTACT_ID, 0)
                .withValue(ContactsContract.Data.MIMETYPE, ContactsContract.CommonDataKinds.Phone.CONTENT_ITEM_TYPE)
                .withValue(ContactsContract.CommonDataKinds.Phone.NUMBER, number)
                .withValue(ContactsContract.CommonDataKinds.Phone.TYPE, ContactsContract.CommonDataKinds.Phone.TYPE_MOBILE)
                .build()
        )
        val results = context.contentResolver.applyBatch(ContactsContract.AUTHORITY, ops)
        val rawContactId = ContentUris_parseId(results[0].uri!!)
        return rawContactId.toString()
    }

    /** Updates the display name and/or phone number of an existing raw contact. */
    fun update(context: Context, rawContactId: String, name: String, number: String): Boolean {
        val resolver = context.contentResolver

        val nameValues = ContentValues().apply {
            put(ContactsContract.CommonDataKinds.StructuredName.DISPLAY_NAME, name)
        }
        val nameUpdated = resolver.update(
            ContactsContract.Data.CONTENT_URI,
            nameValues,
            "${ContactsContract.Data.RAW_CONTACT_ID} = ? AND ${ContactsContract.Data.MIMETYPE} = ?",
            arrayOf(rawContactId, ContactsContract.CommonDataKinds.StructuredName.CONTENT_ITEM_TYPE)
        )

        val numberValues = ContentValues().apply {
            put(ContactsContract.CommonDataKinds.Phone.NUMBER, number)
        }
        val numberUpdated = resolver.update(
            ContactsContract.Data.CONTENT_URI,
            numberValues,
            "${ContactsContract.Data.RAW_CONTACT_ID} = ? AND ${ContactsContract.Data.MIMETYPE} = ?",
            arrayOf(rawContactId, ContactsContract.CommonDataKinds.Phone.CONTENT_ITEM_TYPE)
        )

        return nameUpdated > 0 || numberUpdated > 0
    }

    fun delete(context: Context, rawContactId: String): Boolean {
        val uri = ContactsContract.RawContacts.CONTENT_URI.buildUpon()
            .appendQueryParameter(ContactsContract.CALLER_IS_SYNCADAPTER, "true")
            .build()
        val deleted = context.contentResolver.delete(
            uri,
            "${ContactsContract.RawContacts._ID} = ?",
            arrayOf(rawContactId)
        )
        return deleted > 0
    }

    private fun ContentUris_parseId(uri: Uri): Long = android.content.ContentUris.parseId(uri)
}
