-- The first comment (LinkedIn) or reply (X) that goes with a post: where the
-- link to the model page lives when the platform's rules keep links out of
-- the post itself. Checked with the post for links, handles and quotes.

ALTER TABLE cw_draft ADD COLUMN first_comment text;
