// extern crate proc_macro;
// extern crate syn;
// #[macro_use]
// extern crate quote;

use std::{collections::HashMap};
use proc_macro::{TokenStream};
use quote::{quote, ToTokens};
use syn:: {DeriveInput, Path, punctuated::Punctuated, Token, parse_macro_input, Ident};
// use proc_macro2::{Ident, Span};

#[proc_macro_derive(HelloWorld)]
pub fn derive_trait(input: TokenStream) -> TokenStream {
    let input = parse_macro_input!(input);
    let DeriveInput { ident, attrs, data, .. } = &input;

    let obj = match data {
        syn::Data::Struct(obj) => obj,
        _ => panic!("Only structs supported in From macro")
    };
    let attribute_names = obj.fields.iter().map(|field| {field.ident.as_ref().expect("Structs must contain named fields").clone()}).collect::<Vec<_>>();
    print!(">>>>>>>>>> Struct idents: {:?}", attribute_names);

    let name = input.ident;

    let expanded = quote! {
        impl HelloWorld for #name {
            fn hello_world() {
                println!("Hello, World! from {}", stringify!(#name));
            }
        }
    };

    TokenStream::from(expanded)
}


#[cfg(test)]
mod tests {
    #[test]
    fn it_works() {
        assert_eq!(42, 42);
    }
}
