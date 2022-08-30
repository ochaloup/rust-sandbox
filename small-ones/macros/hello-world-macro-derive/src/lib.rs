// extern crate proc_macro;
// extern crate syn;
// #[macro_use]
// extern crate quote;

// use std::{collections::HashMap};
use proc_macro::{TokenStream};
// use quote::{ToTokens};
use quote::{quote};
// use syn::{Path, punctuated::Punctuated, Token, Ident};
use syn::{DeriveInput, parse_macro_input};
// use proc_macro2::{Ident, Span};

#[proc_macro_derive(HelloWorld)]
pub fn derive_trait(input: TokenStream) -> TokenStream {
    let input = parse_macro_input!(input);
    let DeriveInput { ident, attrs:_, data, .. } = &input;

    let mut output = proc_macro2::TokenStream::new();
    
    let name = ident.clone();
    println!(">>>> name: {:?}", name);
    let expanded = quote! {
        impl HelloWorld for #name {
            fn hello_world() {
                println!("Hello, World! from {}", stringify!(#name));
            }
        }
    };
    output.extend(expanded);
    
    let obj = match data {
        syn::Data::Struct(obj) => obj,
        _ => panic!("Only structs supported in From macro")
    };
    let attributes = obj.fields
        .iter()
        .map(|field| {
            let field_name = field.ident.as_ref().expect("Structs must contain named fields").clone();
            field_name
        })
        .collect::<Vec<_>>();
    println!(">>>> Struct idents: {:?}", attributes);
    let quoted_fields = attributes.iter().map(|attr|{
        quote!(#attr: String)
    })
    .collect::<Vec<_>>();
    let struct_impl = quote! {
        #[derive(Debug)]
        struct OhMyGosh {
            #(#quoted_fields),*
        }
    };
    output.extend(struct_impl);

    output.into()
}


#[cfg(test)]
mod tests {
    #[test]
    fn it_works() {
        assert_eq!(42, 42);
    }
}
